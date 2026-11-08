"""내 체크리스트 API 테스트. DB·시드·규정이 준비되어 있어야 실행되고, 아니면 건너뜁니다.

만든 체크리스트는 테스트가 끝날 때 지웁니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.db import SessionLocal
from app.domains.checklist.saved import items_from_procedure
from app.main import app
from app.models import User
from app.rag import retriever

client = TestClient(app)
OTHER_USER = {"X-Employee-No": "E1002"}
TASK = "국내 출장비 정산"


def test_items_keep_documents_before_steps_in_order():
    items = items_from_procedure(
        {
            "documents": [{"name": "영수증", "detail": "카드", "basis": "제10조"}],
            "steps": [
                {"title": "작성", "detail": "", "basis": "제3조"},
                {"title": "승인", "detail": "", "basis": ""},
            ],
        }
    )
    assert [(i.seq, i.kind, i.title, i.done) for i in items] == [
        (0, "document", "영수증", False),
        (1, "step", "작성", False),
        (2, "step", "승인", False),
    ]


@pytest.fixture
def saved():
    try:
        with SessionLocal() as db:
            ready = retriever.has_documents(db) and db.scalar(
                select(User).where(User.employee_no == "E1002")
            )
    except OperationalError:
        pytest.skip("DB 꺼짐")
    if not ready:
        pytest.skip("시드 또는 규정 적재 전")
    r = client.post("/api/checklists", json={"task": TASK})
    assert r.status_code == 201, r.text
    data = r.json()
    yield data
    client.delete(f"/api/checklists/{data['id']}")


def test_save_copies_the_procedure(saved):
    assert saved["task"] == TASK
    assert saved["deadline"]["text"].startswith("출장을 완료한 날부터 15일")
    assert "부서장을 제외한 직원: 부서장" in saved["approver"]["text"]
    kinds = {i["kind"] for i in saved["items"]}
    assert kinds == {"document", "step"}
    assert all(i["done"] is False for i in saved["items"])
    assert saved["sources"][-1]["article"] == "별표"


def test_list_shows_newest_with_ordered_items(saved):
    data = client.get("/api/checklists").json()
    assert data[0]["id"] == saved["id"]
    assert [i["id"] for i in data[0]["items"]] == [i["id"] for i in saved["items"]]


def test_check_and_uncheck_item(saved):
    url = f"/api/checklists/{saved['id']}/items/{saved['items'][0]['id']}"
    done = client.patch(url, json={"done": True}).json()
    assert done["done"] is True and done["done_at"]
    undone = client.patch(url, json={"done": False}).json()
    assert undone["done"] is False and undone["done_at"] is None


def test_other_user_cannot_see_or_change(saved):
    item_url = f"/api/checklists/{saved['id']}/items/{saved['items'][0]['id']}"
    assert saved["id"] not in [
        c["id"] for c in client.get("/api/checklists", headers=OTHER_USER).json()
    ]
    assert client.patch(item_url, json={"done": True}, headers=OTHER_USER).status_code == 404
    assert client.delete(f"/api/checklists/{saved['id']}", headers=OTHER_USER).status_code == 404


def test_item_of_another_checklist_is_404(saved):
    assert (
        client.patch(f"/api/checklists/{saved['id']}/items/0", json={"done": True}).status_code
        == 404
    )


def test_delete_removes_checklist(saved):
    assert client.delete(f"/api/checklists/{saved['id']}").status_code == 204
    assert saved["id"] not in [c["id"] for c in client.get("/api/checklists").json()]


def test_unknown_task_and_user_are_rejected(saved):
    r = client.post("/api/checklists", json={"task": "연차 신청"})
    assert r.status_code == 400 and "저장할 수 있는 업무" in r.json()["error"]
    r = client.get("/api/checklists", headers={"X-Employee-No": "NOSUCHUSER"})
    assert r.status_code == 401 and "scripts.seed" in r.json()["error"]


def test_blank_task_is_400():
    r = client.post("/api/checklists", json={"task": " "})
    assert r.status_code == 400
    assert r.json() == {"error": "저장할 업무를 알려 주세요."}
