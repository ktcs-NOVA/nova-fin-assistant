"""API 약속(docs/API.md) 테스트 — DB 없이도 돌아가는 것만.

uv run pytest
"""

from fastapi.testclient import TestClient

from app.core.constants import VERDICT_CHECK, VERDICT_FIX, VERDICT_OK
from app.main import app

client = TestClient(app)
VERDICTS = {VERDICT_OK, VERDICT_FIX, VERDICT_CHECK}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_verify_shape():
    body = {
        "trip_type": "국내출장",
        "grade": "직원 3급 이하",
        "items": [{"field": "숙박비", "amount": 80000, "date": "2026-10-20", "note": ""}],
    }
    r = client.post("/api/verify", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["overall"] in VERDICTS
    for item in data["items"]:
        assert {"field", "verdict", "message", "basis", "fix"} <= item.keys()
        assert item["verdict"] in VERDICTS


def test_verify_empty_items_is_400():
    r = client.post("/api/verify", json={"items": []})
    assert r.status_code == 400
    assert r.json() == {"error": "items가 비어 있습니다."}


def test_qa_blank_question_is_400():
    r = client.post("/api/qa", json={"question": "   "})
    assert r.status_code == 400
    assert r.json() == {"error": "질문을 입력해 주세요."}


def test_checklist_shape():
    r = client.get("/api/checklist", params={"type": "국내출장"})
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "국내출장"
    assert all({"id", "text", "basis"} <= i.keys() for i in data["items"])


def test_cors_allows_frontend():
    r = client.options(
        "/api/qa",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
