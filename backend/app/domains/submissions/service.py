"""정산 제출(직원) 과 검토 대기함(관리자, M-01).

흐름: 직원이 U-04 검증을 마친 청구 내역을 제출 → Submission + Expense 저장 (AI 판정 결과 포함)
      → 관리자가 목록·상세를 보고 승인/반려 (Review 기록) → 반려 메시지 초안은 판정 근거로 작성.
승인·반려는 항상 사람이 누릅니다.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai import llm
from app.core.config import settings
from app.core.constants import (
    ROLE_ADMIN,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    VERDICT_OK,
)
from app.core.errors import AppError
from app.domains.verify import service as verify_service
from app.models import Expense, Review, Submission, Trip, User

KST = ZoneInfo("Asia/Seoul")
STEP_ADMIN_REVIEW = 5  # 상단 처리 단계: 5 관리자 검토, 6 예산 반영(처리 완료)
STEP_DONE = 6

# 청구 항목에서 Expense 컬럼으로 바로 옮기는 키. 나머지는 extra(JSON)에 보관
_ITEM_COLUMNS = {"field", "amount", "date", "time", "payment", "merchant", "merchant_type", "note", "attendees"}


def _as_list(value) -> list[str] | None:
    """참석자는 목록으로 저장. 문자열 하나로 와도 받아 줍니다."""
    if not value:
        return None
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value if str(v).strip()] or None


def require_admin(user: User) -> None:
    if user.role != ROLE_ADMIN:
        raise AppError("회계 관리자만 쓸 수 있는 기능입니다.", 403)


# ---------------------------------------------------------------------------
# 직원 제출
# ---------------------------------------------------------------------------
def _parse_date(v) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _parse_time(v) -> time | None:
    if not v:
        return None
    try:
        return time.fromisoformat(str(v))
    except ValueError:
        return None


def _next_code(db: Session, today: date) -> str:
    prefix = f"S-{today.year}-"
    last = db.scalar(
        select(Submission.code).where(Submission.code.like(prefix + "%")).order_by(Submission.code.desc()).limit(1)
    )
    seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{seq:03d}"


def _default_purpose(trip_type: str, trip: dict, items: list[dict]) -> str:
    region = (trip or {}).get("region")
    if "출장" in trip_type:
        span = ", ".join(x for x in [(trip or {}).get("start_date"), region] if x)
        return f"출장 여비 정산 ({span})" if span else "출장 여비 정산"
    first = items[0].get("field") or items[0].get("purpose") or trip_type
    return f"{first} ({trip_type})" if first != trip_type else f"{trip_type} 지출 정산"


def create_submission(db: Session, user: User, req: dict) -> Submission:
    items = req.get("items") or []
    if not items:
        raise AppError("items가 비어 있습니다.")
    trip_type = str(req.get("trip_type") or "국내출장")
    trip_in = dict(req.get("trip") or {})
    now = datetime.now(KST)

    # AI 사전검증: 프론트가 보낸 결과가 있으면 그대로, 없으면 다시 돌림
    claim = {k: v for k, v in req.items() if k not in {"purpose", "account", "verify_result"}}
    verify = req.get("verify_result") or verify_service.verify(claim)

    start, end = _parse_date(trip_in.get("start_date")), _parse_date(trip_in.get("end_date"))
    trip = None
    if start and end:
        trip = Trip(
            user=user,
            title=req.get("purpose") or _default_purpose(trip_type, trip_in, items),
            destination=trip_in.get("region"),
            region=trip_in.get("region"),
            start_date=start,
            end_date=end,
            vehicle=trip_in.get("vehicle"),
            private_car_approved=bool(trip_in.get("private_car_approved")),
        )

    expenses = []
    for it in items:
        amount = int(it.get("amount") or 0)
        if amount <= 0:
            raise AppError(f"'{it.get('field', '항목')}' 금액이 0원 이하입니다.")
        expenses.append(
            Expense(
                user=user,
                trip=trip,
                field=str(it.get("field") or it.get("purpose") or "기타")[:30],
                amount=amount,
                used_date=_parse_date(it.get("date")) or start or now.date(),
                used_time=_parse_time(it.get("time")),
                payment=str(it.get("payment") or ("법인카드" if "출장" not in trip_type else "여비 지급"))[:20],
                merchant=(it.get("merchant") or None),
                merchant_type=(it.get("merchant_type") or it.get("business_type") or None),
                note=(it.get("note") or None),
                attendees=_as_list(it.get("attendees")),
                extra={k: v for k, v in it.items() if k not in _ITEM_COLUMNS and v not in (None, "", False)},
            )
        )

    sub = Submission(
        code=_next_code(db, now.date()),
        user=user,
        type=trip_type,
        purpose=(req.get("purpose") or _default_purpose(trip_type, trip_in, items))[:200],
        total_amount=sum(e.amount for e in expenses),
        account=(req.get("account") or None),
        status=STATUS_PENDING,
        step=STEP_ADMIN_REVIEW,
        verdict=verify.get("overall"),
        verify_result=verify,
        submitted_at=now,
    )
    for e in expenses:
        e.submission = sub
    db.add_all([*([trip] if trip else []), sub, *expenses])
    db.flush()
    if trip:
        sub.trip_id = trip.id
    db.commit()
    return get_submission(db, sub.code)


# ---------------------------------------------------------------------------
# 조회
# ---------------------------------------------------------------------------
def _query():
    return select(Submission).options(
        selectinload(Submission.user),
        selectinload(Submission.expenses),
        selectinload(Submission.reviews),
        selectinload(Submission.trip),
    )


def _claim_from_expenses(sub: Submission) -> dict:
    """DB 에 저장된 지출 항목을 /api/verify 요청 모양으로 (시드처럼 판정 없이 들어온 건용)."""
    trip = sub.trip
    items = [
        {
            "field": e.field, "amount": e.amount, "date": e.used_date.isoformat(),
            "time": e.used_time.strftime("%H:%M") if e.used_time else None,
            "payment": e.payment, "merchant": e.merchant, "merchant_type": e.merchant_type,
            "note": e.note, "attendees": e.attendees, **(e.extra or {}),
        }
        for e in sub.expenses
    ]
    claim = {"trip_type": sub.type, "grade": sub.user.grade, "items": items}
    if trip is not None:
        claim["trip"] = {
            "start_date": trip.start_date.isoformat(), "end_date": trip.end_date.isoformat(),
            "region": trip.region, "vehicle": trip.vehicle, "private_car_approved": trip.private_car_approved,
        }
    return claim


def _ensure_verified(db: Session, sub: Submission) -> None:
    if sub.verify_result or not sub.expenses:
        return
    try:
        result = verify_service.verify(_claim_from_expenses(sub))
    except Exception:  # 검증 실패해도 조회는 되게
        return
    sub.verify_result = result
    sub.verdict = result.get("overall")
    db.commit()


def list_submissions(db: Session, user: User | None = None) -> list[Submission]:
    """user 를 주면 그 사람 것만(직원 '내 제출 내역'), 없으면 전체(관리자)."""
    q = _query().order_by(Submission.submitted_at.desc().nullslast(), Submission.id.desc())
    if user is not None:
        q = q.where(Submission.user_id == user.id)
    rows = list(db.scalars(q))
    for sub in rows:
        _ensure_verified(db, sub)
    return rows


def get_submission(db: Session, code: str) -> Submission:
    sub = db.scalar(_query().where(Submission.code == code))
    if sub is None:
        raise AppError(f"제출 건 {code} 을(를) 찾을 수 없습니다.", 404)
    _ensure_verified(db, sub)
    return sub


def to_view(sub: Submission) -> dict:
    """프론트 목업(submissions.json) 한 건과 같은 모양으로."""
    expenses = sorted(sub.expenses, key=lambda e: (e.used_date, e.used_time or time.min, e.id))
    first = expenses[0] if expenses else None
    last_review = max(sub.reviews, key=lambda r: r.id) if sub.reviews else None
    verify = sub.verify_result or {}
    return {
        "id": sub.code,
        "submitter": sub.user.name,
        "dept": sub.user.department,
        "type": sub.type,
        "purpose": sub.purpose,
        "merchant": first.merchant if first else None,
        "date": first.used_date.isoformat() if first else None,
        "time": first.used_time.strftime("%H:%M") if first and first.used_time else None,
        "amount": sub.total_amount,
        "account": sub.account,
        "submitted_at": sub.submitted_at.astimezone(KST).date().isoformat() if sub.submitted_at else None,
        "step": sub.step,
        "verdict": sub.verdict or verify.get("overall"),
        "status": sub.status,
        "items": verify.get("items", []),
        "expenses": [
            {
                "field": e.field, "amount": e.amount, "date": e.used_date.isoformat(),
                "time": e.used_time.strftime("%H:%M") if e.used_time else None,
                "payment": e.payment, "merchant": e.merchant, "note": e.note,
                "attendees": e.attendees or [],  # 회의비 참석자 (회의 목적은 extra.meeting_purpose)
                **(e.extra or {}),
            }
            for e in expenses
        ],
        "decision_message": last_review.message if last_review else None,
        "decided_at": last_review.created_at.astimezone(KST).date().isoformat() if last_review and last_review.created_at else None,
    }


# ---------------------------------------------------------------------------
# 관리자 승인/반려
# ---------------------------------------------------------------------------
def decide(db: Session, admin: User, code: str, decision: str, message: str) -> Submission:
    if decision not in (STATUS_APPROVED, STATUS_REJECTED):
        raise AppError(f"decision 은 '{STATUS_APPROVED}' 또는 '{STATUS_REJECTED}' 여야 합니다.")
    sub = get_submission(db, code)
    if sub.status != STATUS_PENDING:
        raise AppError(f"이미 '{sub.status}' 처리된 건입니다.", 409)
    message = (message or "").strip()
    if decision == STATUS_REJECTED and not message:
        raise AppError("반려 사유(message)를 적어 주세요.")

    issues = [it for it in (sub.verify_result or {}).get("items", []) if it.get("verdict") != VERDICT_OK]
    db.add(
        Review(
            submission=sub,
            reviewer_id=admin.id,
            decision=decision,
            message=message or None,
            sources=[{"field": it.get("field"), "basis": it.get("basis")} for it in issues] or None,
        )
    )
    sub.status = decision
    sub.step = STEP_DONE
    db.commit()
    return get_submission(db, code)


# ---------------------------------------------------------------------------
# 반려 메시지 초안
# ---------------------------------------------------------------------------
_DRAFT_SYSTEM = (
    "당신은 공공기관 회계 담당자입니다. 아래 '반려 사유 목록'을 바탕으로 직원에게 보낼 반려 안내문을 한국어로 씁니다.\n"
    "규칙: 사유마다 (1) 무엇이 문제인지 (2) 근거 조항 (3) 어떻게 고쳐 다시 내면 되는지를 번호를 붙여 적습니다. "
    "근거 조항은 목록에 있는 것만 그대로 인용하고 새로 만들지 않습니다. 정중하되 짧게, 10줄 안팎으로 씁니다. "
    "받는 사람·건명 같은 머리글이나 제목은 쓰지 말고, 첫 줄은 '○○○님,' 으로 시작하는 본문만 씁니다. "
    "마지막 줄은 '수정 후 다시 제출해 주세요.' 로 끝냅니다."
)


def _rule_based_draft(sub: Submission, picked: list[dict]) -> str:
    lines = [
        f"{i + 1}. [{it.get('field')}] {it.get('message')}\n   - 근거: {it.get('basis') or '-'}\n   - 수정: {it.get('fix') or '담당자와 협의'}"
        for i, it in enumerate(picked)
    ]
    return (
        f"{sub.user.name}님, 제출하신 {sub.purpose} 정산 건은 아래 사유로 반려되었습니다.\n\n"
        + "\n".join(lines)
        + "\n\n수정 후 다시 제출해 주세요."
    )


def reject_draft(db: Session, code: str, issue_fields: list[str], extra_issues: list[dict]) -> dict:
    sub = get_submission(db, code)
    items = (sub.verify_result or {}).get("items", [])
    picked = [it for it in items if it.get("field") in set(issue_fields) and it.get("verdict") != VERDICT_OK]
    picked += [it for it in extra_issues if it.get("field")]
    if not picked:
        raise AppError("반려 사유를 하나 이상 선택해 주세요.")

    draft = _rule_based_draft(sub, picked)
    if not settings.ai_mock:
        try:
            polished = llm.chat(
                _DRAFT_SYSTEM,
                f"받는 사람: {sub.user.name} ({sub.user.department})\n건명: {sub.purpose} / 유형: {sub.type} / 금액: {sub.total_amount:,}원\n\n"
                f"반려 사유 목록:\n{draft}",
                temperature=0.2,
            ).strip()
            if polished:
                draft = polished
        except Exception:  # LLM 실패 시 규칙 기반 초안으로
            pass
    return {"message": draft, "sources": [it.get("basis") for it in picked if it.get("basis")]}
