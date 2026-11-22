"""규정 원문 보기 API 테스트. 적재된 규정이 있어야 해서 DB·시드가 없으면 건너뜁니다."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.constants import AUDIENCE_ADMIN
from app.core.db import SessionLocal
from app.core.security import create_token
from app.main import app
from app.models.knowledge import Document

client = TestClient(app)


def auth(employee_no: str) -> dict:
    return {"Authorization": f"Bearer {create_token(employee_no)}"}


@pytest.fixture(scope="module")
def docs():
    """적재된 현행 규정: (직원도 보는 것, 관리자만 보는 것)."""
    try:
        with SessionLocal() as db:
            rows = db.scalars(select(Document).where(Document.is_current.is_(True))).all()
            open_ids = [d.id for d in rows if d.audience != AUDIENCE_ADMIN]
            admin_ids = [d.id for d in rows if d.audience == AUDIENCE_ADMIN]
    except OperationalError:
        pytest.skip("DB 꺼짐")
    if not open_ids:
        pytest.skip("규정 적재 전")
    return open_ids, admin_ids


def test_needs_login():
    assert client.get("/api/regulations").status_code == 401


def test_employee_sees_only_employee_regulations(docs):
    open_ids, admin_ids = docs
    listed = client.get("/api/regulations", headers=auth("E1001")).json()
    assert {r["id"] for r in listed} == set(open_ids)
    assert all(not r["admin_only"] and r["sections"] > 0 for r in listed)
    if admin_ids:  # 관리자용 규정은 주소를 알아도 직원에게는 없는 것으로
        assert client.get(f"/api/regulations/{admin_ids[0]}", headers=auth("E1001")).status_code == 404


def test_admin_sees_admin_regulations_too(docs):
    open_ids, admin_ids = docs
    listed = client.get("/api/regulations", headers=auth("A2001")).json()
    assert {r["id"] for r in listed} == set(open_ids) | set(admin_ids)


def test_text_comes_in_document_order_unchanged(docs):
    open_ids, _ = docs
    reg = client.get(f"/api/regulations/{open_ids[0]}", headers=auth("E1001")).json()
    seqs = [s["seq"] for s in reg["sections"]]
    assert seqs == sorted(seqs) and len(seqs) > 0
    assert all(s["content"].strip() and s["type"] in ("article", "table", "form") for s in reg["sections"])
    assert client.get("/api/regulations/999999", headers=auth("E1001")).status_code == 404
