"""U-02 업무절차·필요서류 안내 요청·응답 모양 (docs/API.md 3-4). 바꾸기 전에 프론트 담당에게 먼저 알리기."""

from pydantic import BaseModel, Field, field_validator

from app.domains.sources import Source


class ProcedureRequest(BaseModel):
    task: str = Field(max_length=200, examples=["국내 출장비 정산하려면?"])

    @field_validator("task")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("알고 싶은 업무를 입력해 주세요.")
        return v


class DocumentItem(BaseModel):
    name: str  # 필요 서류 이름
    detail: str = ""
    basis: str = ""  # 근거 조항


class StepItem(BaseModel):
    title: str  # 작성 순서 한 단계
    detail: str = ""
    basis: str = ""


class Fact(BaseModel):
    text: str
    basis: str = ""
    check: bool = False  # True 면 규정만으로 확정할 수 없어 "담당자 확인 필요" 표시


class ProcedureResponse(BaseModel):
    task: str
    summary: str = ""
    documents: list[DocumentItem] = []  # ① 필요 서류
    steps: list[StepItem] = []  # ② 작성 순서
    deadline: Fact | None = None  # ③ 제출 기한
    approver: Fact | None = None  # ④ 결재자 (위임전결 기준)
    grounded: bool = True
    sources: list[Source] = []
