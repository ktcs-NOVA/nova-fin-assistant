"""경로 조회 테스트. 네이버 API 는 부르지 않고, 문서에 나온 응답 모양을 흉내 낸 가짜 응답으로 확인합니다."""

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.errors import AppError
from app.domains.route import service
from app.main import app

GEO = {
    "부산광역시 해운대구 마린시티2로 38": {"addresses": [{"x": "129.1415", "y": "35.1556", "roadAddress": "부산광역시 해운대구 마린시티2로 38"}]},
    "부산광역시 연제구 중앙대로 1001": {"addresses": [{"x": "129.0750", "y": "35.1798", "roadAddress": "부산광역시 연제구 중앙대로 1001"}]},
}
ROUTE_OK = {"code": 0, "message": "길찾기를 성공하였습니다.", "route": {"traoptimal": [{"summary": {"distance": 12345, "duration": 1500000}}]}}


@pytest.fixture
def naver(monkeypatch):
    """키가 있는 것처럼 만들고, 불린 주소를 기록하는 가짜 네이버 API."""
    calls: list[str] = []
    state = {"route": ROUTE_OK, "place": {"items": [{"title": "<b>부산시청</b>", "roadAddress": "부산광역시 연제구 중앙대로 1001"}]}}

    def fake(url, headers):
        calls.append(url)
        if "map-geocode" in url:
            assert headers["x-ncp-apigw-api-key-id"] == "id" and headers["x-ncp-apigw-api-key"] == "key"
            q = service.urllib.parse.parse_qs(url.split("?", 1)[1])["query"][0]
            return GEO.get(q, {"addresses": []})
        if "search/local" in url:
            assert headers["X-Naver-Client-Id"] == "cid"
            return state["place"]
        assert "start=129.1415%2C35.1556" in url and "goal=129.0750%2C35.1798" in url  # 경도,위도 순서
        return state["route"]

    monkeypatch.setattr(settings, "naver_maps_key_id", "id")
    monkeypatch.setattr(settings, "naver_maps_key", "key")
    monkeypatch.setattr(settings, "naver_search_client_id", "")
    monkeypatch.setattr(settings, "naver_search_client_secret", "")
    monkeypatch.setattr(service, "_get_json", fake)
    monkeypatch.setattr(service, "_origin", None)
    service._cache.clear()
    return calls, state


def test_address_gives_one_way_km_and_minutes(naver):
    calls, _ = naver
    r = service.lookup("  부산광역시 연제구   중앙대로 1001 ")
    assert r == {"destination": "부산광역시 연제구 중앙대로 1001", "distance_km": 12.3, "duration_min": 25}
    assert len(calls) == 3  # 도착지 좌표 → 회사 좌표 → 경로
    service.lookup("부산광역시 연제구 중앙대로 1001")
    assert len(calls) == 3  # 같은 곳은 다시 부르지 않음


def test_place_name_needs_search_key(naver, monkeypatch):
    with pytest.raises(AppError) as e:  # 검색 키가 없으면 장소 이름은 못 찾음
        service.lookup("부산시청")
    assert e.value.status_code == 404 and "주소" in e.value.message
    monkeypatch.setattr(settings, "naver_search_client_id", "cid")
    monkeypatch.setattr(settings, "naver_search_client_secret", "sec")
    r = service.lookup("부산시청")
    assert r["destination"] == "부산시청 (부산광역시 연제구 중앙대로 1001)" and r["distance_km"] == 12.3


def test_route_failure_codes_become_messages(naver):
    _, state = naver
    state["route"] = {"code": 2, "message": "출발지 또는 도착지가 도로 주변이 아닙니다."}
    with pytest.raises(AppError) as e:
        service.lookup("부산광역시 연제구 중앙대로 1001")
    assert e.value.status_code == 404 and "도로 주변" in e.value.message


def test_without_keys_tells_to_type_distance(monkeypatch):
    monkeypatch.setattr(settings, "naver_maps_key_id", "")
    with pytest.raises(AppError) as e:
        service.lookup("부산시청")
    assert e.value.status_code == 503 and "직접 입력" in e.value.message


def test_api_requires_login_and_reports_not_configured(monkeypatch):
    client = TestClient(app)
    assert client.post("/api/route", json={"destination": "부산시청"}).status_code == 401
    monkeypatch.setattr(settings, "naver_maps_key_id", "")
    app.dependency_overrides[get_current_user] = lambda: object()  # 로그인한 것으로 침 (DB 없이)
    try:
        r = client.post("/api/route", json={"destination": "부산시청"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert r.status_code == 503 and "직접 입력" in r.json()["error"]
