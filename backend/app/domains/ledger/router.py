"""지출내역 엑셀 내려받기: 직원은 내 정산 건, 회계 관리자는 전체. 반려한 건은 넣지 않습니다."""

from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.constants import STATUS_REJECTED
from app.core.db import get_db
from app.domains.ledger import excel
from app.domains.submissions import service as submissions
from app.models import User

router = APIRouter(prefix="/api", tags=["지출내역 엑셀"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
KST = ZoneInfo("Asia/Seoul")


def _file(db: Session, user: User, everyone: bool) -> Response:
    rows = submissions.list_submissions(db, None if everyone else user)
    views = [submissions.to_view(s) for s in rows if s.status != STATUS_REJECTED]
    today = datetime.now(KST).date()
    data = excel.build(
        views,
        writer=user.name,
        dept=user.department or "",
        scope="전체 제출 건" if everyone else "내 정산 건",
        today=today,
        with_name=everyone,
    )
    name = f"지출내역_{'전체' if everyone else user.name}_{today:%Y%m%d}.xlsx"
    return Response(data, media_type=XLSX, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})


@router.get("/ledger", summary="내 정산 건의 지출내역 엑셀 (.xlsx)", response_class=Response)
def my_ledger(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _file(db, user, everyone=False)


@router.get("/admin/ledger", summary="전체 제출 건의 지출내역 엑셀 (.xlsx)", response_class=Response)
def all_ledger(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    submissions.require_admin(user)
    return _file(db, user, everyone=True)
