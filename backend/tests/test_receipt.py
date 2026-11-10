"""U-06 영수증 인식 API — 키 없이(목업) 돌아가는 것만."""

import base64

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domains.receipt.schemas import PURPOSES
from app.domains.receipt.service import _clean
from app.main import app

client = TestClient(app)
# 1x1 PNG
PNG = base64.b64encode(
    bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c636000020000050001e2"
                  "26059b0000000049454e44ae426082")
).decode()


@pytest.fixture(autouse=True)
def mock_ai(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")


def test_receipt_mock_shape():
    r = client.post("/api/receipt", json={"filename": "a.png", "media_type": "image/png", "image_base64": PNG})
    assert r.status_code == 200
    data = r.json()
    assert {"merchant", "total_amount", "date", "time", "items", "purpose_candidates", "confidence", "notes"} <= data.keys()
    assert data["confidence"] in ("high", "medium", "low")
    assert set(data["purpose_candidates"]) <= set(PURPOSES)
    assert "목업" in data["notes"]


def test_receipt_accepts_data_uri_prefix():
    r = client.post("/api/receipt", json={"media_type": "image/png", "image_base64": "data:image/png;base64," + PNG})
    assert r.status_code == 200


def test_receipt_bad_media_type_is_400():
    r = client.post("/api/receipt", json={"media_type": "image/gif", "image_base64": PNG})
    assert r.status_code == 400
    assert "지원하지 않는" in r.json()["error"]


def test_receipt_empty_image_is_400():
    r = client.post("/api/receipt", json={"media_type": "image/jpeg", "image_base64": ""})
    assert r.status_code == 400
    assert r.json() == {"error": "사진 데이터가 비어 있습니다."}


def test_clean_normalizes_model_output():
    out = _clean({
        "total_amount": "6,000원", "card_last4": "****-****-****-1234", "confidence": "확실",
        "purpose_candidates": ["식비", "선물", "식비", "회의비", "기타"],
        "items": [{"name": "라떼", "amount": "6,000"}, "garbage"],
    })
    assert out["total_amount"] == 6000
    assert out["card_last4"] == "1234"
    assert out["confidence"] == "medium"
    assert out["purpose_candidates"] == ["식비", "회의비", "기타"]
    assert out["items"] == [{"name": "라떼", "amount": 6000}]


def test_clean_masked_card_is_unknown():
    assert _clean({"card_last4": "52393000********"})["card_last4"] is None
    assert _clean({"card_last4": "5239-3000-1234-5678"})["card_last4"] == "5678"
    assert _clean({"card_last4": "5239-****-****-5678"})["card_last4"] == "5678"
    assert _clean({"card_last4": "12"})["card_last4"] is None
    assert _clean({"card_number": "5239-3000-****-****"})["card_last4"] is None
    assert _clean({"card_number": "************1234"})["card_last4"] == "1234"
    assert "card_number" not in _clean({"card_number": "1234"})
    assert _clean({"card_number": "3600"})["card_last4"] is None  # 카드번호 길이가 아니면 버림


def test_clean_masks_personal_numbers():
    out = _clean({
        "approval_no": "30004889",
        "notes": "카드번호는 52393000******** 로 가려짐. 가맹점 전화 010-3927-6159, 대표번호 1588-1234, "
                 "사업자번호 311-10-30169, 매장 전화 02-541-5488. 날짜 2026-11-01 은 그대로.",
    })
    assert out["approval_no"] == "****4889"
    for secret in ("52393000", "3927-6159", "1588-1234", "311-10-30169", "541-5488"):
        assert secret not in out["notes"]
    assert "2026-11-01" in out["notes"]
    assert _clean({"approval_no": "[30004889] KICC로제출"})["approval_no"] == "****4889"
    assert _clean({"approval_no": None})["approval_no"] is None
    assert _clean({"approval_no": "없음"})["approval_no"] is None


def test_mock_result_has_no_full_numbers():
    r = client.post("/api/receipt", json={"media_type": "image/png", "image_base64": PNG})
    assert r.json()["approval_no"].startswith("****")
