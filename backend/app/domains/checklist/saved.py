"""직원이 저장한 업무 체크리스트 (U-02).

저장할 내용은 프론트가 보낸 값을 믿지 않고, 업무 이름으로 절차 안내를 다시 만들어 복사합니다.
다른 사람의 체크리스트는 없는 것처럼 404 로 답합니다.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.domains.procedure import service as procedure_service
from app.models import Checklist, ChecklistItem, User

KIND_DOCUMENT = "document"
KIND_STEP = "step"


def items_from_procedure(procedure: dict) -> list[ChecklistItem]:
    """절차 안내의 필요 서류와 작성 순서를 체크 항목으로 바꿉니다."""
    rows = [(KIND_DOCUMENT, d["name"], d) for d in procedure["documents"]]
    rows += [(KIND_STEP, s["title"], s) for s in procedure["steps"]]
    return [
        ChecklistItem(
            seq=i, kind=kind, title=title, detail=row["detail"], basis=row["basis"], done=False
        )
        for i, (kind, title, row) in enumerate(rows)
    ]


def list_checklists(db: Session, user: User) -> list[Checklist]:
    return list(
        db.scalars(
            select(Checklist)
            .where(Checklist.user_id == user.id)
            .options(selectinload(Checklist.items))
            .order_by(Checklist.created_at.desc(), Checklist.id.desc())
        )
    )


def create_checklist(db: Session, user: User, task: str) -> Checklist:
    procedure = procedure_service.get_procedure_by_name(db, task)
    if procedure is None or not procedure["grounded"]:
        raise AppError("체크리스트로 저장할 수 있는 업무가 아닙니다.")
    checklist = Checklist(
        user_id=user.id,
        task=procedure["task"],
        summary=procedure["summary"],
        deadline=procedure["deadline"],
        approver=procedure["approver"],
        sources=procedure["sources"],
        items=items_from_procedure(procedure),
    )
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    return checklist


def _own_checklist(db: Session, user: User, checklist_id: int) -> Checklist:
    checklist = db.scalar(
        select(Checklist).where(Checklist.id == checklist_id, Checklist.user_id == user.id)
    )
    if checklist is None:
        raise AppError("체크리스트를 찾을 수 없습니다.", 404)
    return checklist


def update_item(
    db: Session, user: User, checklist_id: int, item_id: int, done: bool
) -> ChecklistItem:
    checklist = _own_checklist(db, user, checklist_id)
    item = next((x for x in checklist.items if x.id == item_id), None)
    if item is None:
        raise AppError("체크 항목을 찾을 수 없습니다.", 404)
    item.done = done
    item.done_at = datetime.now(UTC) if done else None
    db.commit()
    db.refresh(item)
    return item


def delete_checklist(db: Session, user: User, checklist_id: int) -> None:
    db.delete(_own_checklist(db, user, checklist_id))
    db.commit()
