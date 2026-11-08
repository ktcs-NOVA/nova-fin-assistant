"""U-02 에서 안내하는 업무와 절차. 업무를 추가하려면 TASKS 에 한 항목만 더하면 됩니다.

틀리면 곤란한 안내라 서류·순서·기한을 LLM 에 맡기지 않고 여기에 조항과 함께 적어 둡니다.
각 근거의 phrase 는 조항에 실제로 있어야 하는 표현입니다. 규정이 개정되어 표현이 사라지면
옛 내용을 안내하지 않고 "담당자 확인 필요"로 답하므로, 그때 이 파일을 함께 고치면 됩니다.
"""

from dataclasses import dataclass

TRAVEL = "여비규정"
CARD = "법인카드 관리 및 사용 지침"
BUSINESS = "업무추진비 및 조직관리비 집행 지침"
DELEGATION = "위임전결규정 시행세칙"

# 시행세칙 별표에 항목이 없으면 제5조 제2항이 정한 방법을 안내합니다
NO_APPROVAL_ROW = (
    "시행세칙 별표에 이 업무의 항목이 따로 없습니다. "
    "유사한 업무의 기준을 따르고, 유사 사항이 없으면 주관 부서장이 전결권자를 정합니다."
)
NO_APPROVAL_ROW_BASIS = f"{DELEGATION} 제5조 제2항"
APPROVAL_NOTE = "※ 사장직속"  # 부서장 전결 행에 함께 적용되는 예외 안내


@dataclass(frozen=True)
class Cite:
    """근거 하나. phrase 는 그 조항에 있어야 하는 표현입니다."""

    regulation: str
    article: str
    paragraph: str  # 제2항. 항이 없으면 빈 문자열
    phrase: str

    @property
    def label(self) -> str:
        return " ".join(x for x in (self.regulation, self.article, self.paragraph) if x)


@dataclass(frozen=True)
class Item:
    """필요 서류 한 건 또는 처리 순서 한 단계."""

    name: str
    detail: str
    cites: tuple[Cite, ...]


@dataclass(frozen=True)
class Deadline:
    text: str
    cites: tuple[Cite, ...]
    check: bool = False  # 규정만으로 확정할 수 없으면 True


@dataclass(frozen=True)
class ProcedureTask:
    name: str
    all_of: tuple[tuple[str, ...], ...]  # 묶음마다 단어 하나 이상이 질문에 있어야 함
    summary: str
    documents: tuple[Item, ...]
    steps: tuple[Item, ...]
    deadline: Deadline
    approval_prefix: str | None = None  # 시행세칙 별표에서 찾을 행의 앞부분
    subject_suffix: str = (
        ""  # 행 이름에서 지울 말 ('부서·부서장 업무추진비 … 결의' → '부서·부서장')
    )
    none_of: tuple[str, ...] = ()  # 이 단어가 있으면 다른 업무


_TRIP = ("출장", "여비")
_SETTLE = ("정산", "출장비", "여비", "비용")

# ---------- 출장비 정산 (국내·국외 공통) ----------
_TRIP_FORM = Item(
    "출장원(정산)",
    "별지 제3호 서식. 여비를 정확히 계산해 작성합니다.",
    (
        Cite(TRAVEL, "별지 제3호 서식", "", "출장원(정산)"),
        Cite(TRAVEL, "제3조의2", "제3항", "여비를 정확히 계산"),
    ),
)
_TRIP_REPORT = Item(
    "출장보고서",
    "별지 제4호 서식.",
    (Cite(TRAVEL, "별지 제4호 서식", "", "출장보고서"),),
)
_TRIP_RECEIPT = Item(
    "교통비·숙박비 청구서와 영수증",
    "신용카드영수증이 원칙입니다. 청구서 발행이 곤란하면 영수증만 낼 수 있고, "
    "영수증 제출이 어려운 지역이면 제공자의 자필서명 또는 날인 확인서로 대신할 수 있습니다.",
    (
        Cite(TRAVEL, "제10조", "제1항", "청구서(Invoice"),
        Cite(TRAVEL, "제10조", "제2항", "신용카드영수증을 원칙"),
        Cite(TRAVEL, "제10조", "제3항", "확인서"),
    ),
)
_TRIP_LODGING = Item(
    "숙박시설 발행 청구서",
    "숙박비를 실비 정산할 때 냅니다. 상호명, 투숙자명, 호실, 투숙기간, 요금산출내역이 있어야 합니다.",
    (Cite(TRAVEL, "제11조", "제2항", "투숙자명"),),
)
_STEP_WRITE = Item(
    "출장원(정산)과 출장보고서 작성",
    "여비를 정확히 계산해 작성합니다.",
    (Cite(TRAVEL, "제3조의2", "제3항", "여비를 정확히 계산"),),
)
_STEP_ATTACH = Item(
    "증빙 첨부",
    "교통비와 숙박비 증빙을 붙입니다. 숙박비 청구서에 조식대가 포함되어 있으면 식비의 3분의 1을 차감합니다.",
    (
        Cite(TRAVEL, "제10조", "제1항", "출장 결과 보고 시"),
        Cite(TRAVEL, "제11조", "제4항", "3분의 1을 차감"),
    ),
)
_STEP_APPROVE = Item(
    "출장결과보고 승인",
    "출장승인권자가 여비 금액과 증빙서류를 확인하고 승인합니다.",
    (Cite(TRAVEL, "제3조의2", "제3항", "출장결과보고를 승인"),),
)
_TRIP_DEADLINE = Cite(TRAVEL, "제3조의2", "제2항", "15일 이내")


# 앞에서부터 찾습니다. '국외 출장 정산'이 국내로 잡히지 않도록 국외를 먼저 둡니다.
TASKS: tuple[ProcedureTask, ...] = (
    ProcedureTask(
        name="국외 출장비 정산",
        all_of=(_TRIP, ("국외", "해외", "외국"), _SETTLE),
        summary=(
            "출장원(정산)과 출장보고서에 증빙을 붙여 출장을 완료한 날부터 15일 이내에 정산합니다. "
            "준비금과 공적 항공마일리지 관련 자료가 필요한 경우도 확인합니다."
        ),
        documents=(
            _TRIP_FORM,
            _TRIP_REPORT,
            _TRIP_RECEIPT,
            _TRIP_LODGING,
            Item(
                "준비금 증빙서류",
                "준비금(비자발급비, 예방접종비, 여행자보험 가입비 등)을 받을 때 "
                "세부 사용내용을 확인할 수 있는 서류를 냅니다.",
                (Cite(TRAVEL, "제30조", "제2항", "세부 사용내용"),),
            ),
            Item(
                "공적 항공마일리지 미사용 자료",
                "마일리지를 활용하지 않은 경우 보유 현황, 항공사·여행사 확인자료, "
                "항공권별 운임 비교자료 중 하나를 출장 결과보고 때 냅니다.",
                (Cite(TRAVEL, "제42조", "제2항", "항공권별 운임 비교자료"),),
            ),
        ),
        steps=(
            _STEP_WRITE,
            _STEP_ATTACH,
            Item(
                "준비금 정산 신청",
                "준비금이 있으면 국외출장 전 또는 출장을 마친 날부터 15일 이내에 정산지급을 신청합니다.",
                (Cite(TRAVEL, "제30조", "제2항", "정산지급을 신청"),),
            ),
            _STEP_APPROVE,
        ),
        deadline=Deadline(
            "출장을 완료한 날부터 15일 이내. 법인카드 결제내역이 기한 안에 통보되지 않으면 "
            "카드 매입정보 통보일부터 1주일 이내까지 연장할 수 있습니다. "
            "준비금은 국외출장 전 또는 출장을 마친 날부터 15일 이내에 신청합니다.",
            (_TRIP_DEADLINE, Cite(TRAVEL, "제30조", "제2항", "15일 이내")),
        ),
        approval_prefix="9. 직원복무 > 국외출장",
    ),
    ProcedureTask(
        name="업무추진비 집행",
        all_of=(
            ("업무추진비", "조직관리비"),
            ("집행", "사용", "쓰", "절차", "결의", "처리", "정산", "결제"),
        ),
        summary=(
            "법인카드로 집행합니다. 건당 50만원 이상은 사전에 전사예산관리자의 결재를 받고, "
            "100만원 이상은 그 뒤 일상감사까지 받은 다음 집행합니다."
        ),
        documents=(
            Item(
                "초과 사용신청서",
                "별지 제1호 서식. 건당 50만원 이상 집행하거나 분기 한도 초과가 예상될 때 작성합니다.",
                (
                    Cite(BUSINESS, "제3조", "제4항", "별지 제1호 서식"),
                    Cite(BUSINESS, "제4조", "제2항", "별지 제1호 서식"),
                ),
            ),
            Item(
                "사용 내역",
                "카드 사용자, 총인원수, 상대방 소속·직책·성명 등 업무관련성을 입증하는 내용입니다. "
                "전사예산관리자가 요구하는 양식으로 내며, 예산관리시스템으로 갈음할 수 있습니다.",
                (Cite(BUSINESS, "제8조", "제1항", "상대방 소속"),),
            ),
            Item(
                "사용실적 (임원만)",
                "별지 제3호 서식. 업무추진비를 사용한 임원이 당월 실적을 작성합니다.",
                (Cite(BUSINESS, "제8조", "제1항", "각 임원의 경우"),),
            ),
            Item(
                "경조 사실·업무 관련성 증빙 (경조금을 현금으로 낼 때)",
                "전결권자의 결재를 받아 전사예산관리자에게 제출합니다.",
                (Cite(BUSINESS, "제4조", "제1항", "경조 사실 및 업무 관련성"),),
            ),
        ),
        steps=(
            Item(
                "분기 한도 확인",
                "한도 초과가 예상되면 전사예산관리자에게 지출 가능 여부를 확인하고 "
                "별지 제1호 서식으로 사전 승인을 받습니다.",
                (Cite(BUSINESS, "제4조", "제2항", "사전에 제출하여 승인"),),
            ),
            Item(
                "사전 결재",
                "건당 50만원 이상이면 별지 제1호 서식으로 전사예산관리자의 결재를 받습니다. "
                "100만원 이상이면 그 뒤 일상감사도 받습니다. "
                "50만원 미만으로 나눠 결제해도 거래 실질이 1건이면 1건으로 봅니다.",
                (
                    Cite(BUSINESS, "제3조", "제4항", "일상감사"),
                    Cite(BUSINESS, "제3조", "제5항", "1건으로 보아"),
                ),
            ),
            Item(
                "법인카드로 집행",
                "반드시 법인카드로 지출합니다. 경조금은 현금도 가능합니다. "
                "사용 업종과 시간은 법인카드 지침을 따릅니다.",
                (
                    Cite(BUSINESS, "제4조", "제1항", "반드시 법인카드"),
                    Cite(BUSINESS, "제9조", "", "사용시간"),
                ),
            ),
            Item(
                "사용 내역 제출",
                "집행자가 업무관련성 입증 내용을 제출합니다.",
                (Cite(BUSINESS, "제8조", "제1항", "집행자는"),),
            ),
        ),
        deadline=Deadline(
            "임원은 당월 사용실적을 익월 8영업일까지 제출합니다. "
            "임원이 아닌 집행자의 제출 기한은 지침에 없어 전사예산관리자 확인이 필요합니다.",
            (Cite(BUSINESS, "제8조", "제1항", "익월 8영업일"),),
            check=True,
        ),
        approval_prefix="11. 업무추진비 및 조직관리비 집행 결의",
        subject_suffix=" 업무추진비 및 조직관리비 집행 결의",
    ),
    ProcedureTask(
        name="국내 출장비 정산",
        all_of=(_TRIP, _SETTLE),
        summary="출장원(정산)과 출장보고서에 교통비·숙박비 증빙을 붙여 출장을 완료한 날부터 15일 이내에 정산합니다.",
        documents=(_TRIP_FORM, _TRIP_REPORT, _TRIP_RECEIPT, _TRIP_LODGING),
        steps=(_STEP_WRITE, _STEP_ATTACH, _STEP_APPROVE),
        deadline=Deadline(
            "출장을 완료한 날부터 15일 이내. 법인카드 결제내역이 기한 안에 통보되지 않으면 "
            "카드 매입정보 통보일부터 1주일 이내까지 연장할 수 있습니다.",
            (_TRIP_DEADLINE,),
        ),
        approval_prefix="9. 직원복무 > 국내출장",
    ),
    ProcedureTask(
        name="법인카드 사용 후 처리",
        all_of=(
            ("법인카드", "법카", "회사카드"),
            ("사용", "쓰", "결제", "처리", "정산", "결의", "영수증", "전표", "절차"),
        ),
        none_of=("분실", "도난", "발급", "한도"),
        summary="카드 사용 후 10일 이내에 사용내역을 전산시스템에 입력하고 별지 제6호 서식을 첨부해 지출결의합니다.",
        documents=(
            Item(
                "별지 제6호 서식",
                "전산시스템에 사용내역을 입력한 뒤 지출결의에 첨부합니다.",
                (Cite(CARD, "제8조", "제3항", "별지 제6호 서식"),),
            ),
            Item(
                "별지 제5호 서식 (해당하는 경우)",
                "공휴일·휴무일 사용, 23시~익일 06시 사용, 기타주점업 사용이면 "
                "지출결의서에 첨부합니다. 업무상 불가피하고 객관적으로 증명할 수 있어야 합니다.",
                (Cite(CARD, "제10조", "제4항", "비정상시간대"),),
            ),
        ),
        steps=(
            Item(
                "매출전표 확인",
                "이용금액과 상호가 맞는지 확인하고 성명을 기재합니다.",
                (Cite(CARD, "제7조", "제7항", "자필로 성명"),),
            ),
            Item(
                "사용내역 입력과 지출결의",
                "팀별로 배부된 카드는 사용직원이, 부서장 이상에게 배부된 카드는 관리부서에서 지출결의합니다.",
                (
                    Cite(CARD, "제8조", "제1항", "관리부서에서 지출결의"),
                    Cite(CARD, "제8조", "제3항", "전산시스템"),
                ),
            ),
            Item(
                "주관부서 확인",
                "주관부서가 적정성을 확인하고 대금결제를 진행합니다. "
                "정정을 요청받으면 관리부서가 다음 영업일까지 반영합니다.",
                (
                    Cite(CARD, "제8조", "제4항", "적정성"),
                    Cite(CARD, "제8조", "제6항", "익일"),
                ),
            ),
        ),
        deadline=Deadline(
            "카드 사용 후 10일 이내. 장기출장 등 불가피한 경우에는 그 사유가 없어진 날부터 7일 이내에 "
            "처리할 수 있고, 월 마감 때는 결산일정에 따릅니다. 기한을 넘겨 생긴 연체료는 사용직원이 부담합니다.",
            (
                Cite(CARD, "제8조", "제1항", "10일 이내"),
                Cite(CARD, "제8조", "제2항", "결산일정"),
            ),
        ),
    ),
)


def match_task(question: str) -> ProcedureTask | None:
    text = "".join(question.split())
    for task in TASKS:
        if any(word in text for word in task.none_of):
            continue
        if all(any(word in text for word in group) for group in task.all_of):
            return task
    return None
