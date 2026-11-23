"""경로 조회 (POST /api/route): 네이버 응답을 가짜로 바꿔 끼워 키·네트워크 없이 확인합니다."""

import pytest

from app.core.config import settings
from app.core.errors import AppError
from app.domains.route import service

ORIGIN = {"x": "129.1427", "y": "35.1563", "roadAddress": "부산광역시 해운대구 마린시티2로 38"}
CITY_HALL = {"x": "129.0756", "y": "35.1798", "roadAddress": "부산광역시 연제구 중앙대로 1001"}


@pytest.fixture
def naver(monkeypatch):
    """키를 넣은 상태로 만들고, 바깥 호출을 가짜 응답으로 바꿉니다. calls 에 부른 주소가 쌓입니다."""
    monkeypatch.setattr(settings, "naver_maps_client_id", "id")
    monkeypatch.setattr(settings, "naver_maps_client_secret", "secret")
    monkeypatch.setattr(settings, "naver_search_client_id", "")
    monkeypatch.setattr(settings, "naver_search_client_secret", "")
    service.reset_cache()
    calls = []
    answers = {
        "geocode": lambda q: (
            {"addresses": [CITY_HALL] if "1001" in q or "연제구" in q else []}
            if q != settings.route_origin_address
            else {"addresses": [ORIGIN]}
        ),
        "driving": {
            "code": 0,
            "route": {"traoptimal": [{"summary": {"distance": 12345, "duration": 1_500_000}}]},
        },
        "local": {
            "items": [
                {"title": "<b>부산시청</b>", "roadAddress": "부산광역시 연제구 중앙대로 1001"}
            ]
        },
    }

    def fake_fetch(url, params, headers):
        calls.append(url)
        if url.endswith("/geocode"):
            return answers["geocode"](params["query"])
        if url.endswith("/driving"):
            return answers["driving"]
        return answers["local"]

    monkeypatch.setattr(service, "fetch", fake_fetch)
    return calls, answers, monkeypatch


def test_address_to_one_way_distance(naver):
    calls, _, _ = naver
    result = service.lookup("부산광역시 연제구 중앙대로 1001")
    assert result == {
        "destination": "부산광역시 연제구 중앙대로 1001",
        "distance_km": 12.3,
        "duration_min": 25,
    }
    service.lookup("부산광역시 연제구 중앙대로 1001")  # 같은 도착지는 다시 부르지 않음
    assert sum(u.endswith("/driving") for u in calls) == 1


def test_place_name_uses_local_search_when_key_exists(naver):
    _, _, monkeypatch = naver
    with pytest.raises(AppError) as e:  # 검색 키가 없으면 장소 이름은 못 찾음
        service.lookup("부산시청")
    assert e.value.status_code == 404

    monkeypatch.setattr(settings, "naver_search_client_id", "cid")
    monkeypatch.setattr(settings, "naver_search_client_secret", "csecret")
    result = service.lookup("부산시청")
    assert result["destination"] == "부산시청 (부산광역시 연제구 중앙대로 1001)"  # <b> 태그는 지움


def test_directions_error_code_is_explained(naver):
    _, answers, _ = naver
    answers["driving"] = {"code": 1, "message": "출발지와 도착지가 동일합니다."}
    with pytest.raises(AppError) as e:
        service.lookup("부산광역시 연제구 중앙대로 1001")
    assert e.value.status_code == 404 and "같은 곳" in e.value.message


def test_without_keys_asks_to_type_distance(monkeypatch):
    monkeypatch.setattr(settings, "naver_maps_client_id", "")
    with pytest.raises(AppError) as e:
        service.lookup("부산광역시 연제구 중앙대로 1001")
    assert e.value.status_code == 503 and "직접 입력" in e.value.message


def test_blank_destination_is_rejected(naver):
    with pytest.raises(AppError) as e:
        service.lookup("   ")
    assert e.value.status_code == 400


def test_place_search_prefers_institution_over_restaurant_branch(naver):
    _, answers, monkeypatch = naver
    monkeypatch.setattr(settings, "naver_search_client_id", "cid")
    monkeypatch.setattr(settings, "naver_search_client_secret", "csecret")
    answers["local"] = {
        "items": [
            {
                "title": "1988평화숯불구이 <b>대전시청</b>점",
                "category": "음식점>한식>육류,고기요리",
                "roadAddress": "부산광역시 연제구 중앙대로 1001",
            },
            {
                "title": "대전광역시청",
                "category": "공공,사회기관>특별,광역시청",
                "roadAddress": "부산광역시 연제구 중앙대로 1001",
            },
        ]
    }
    result = service.lookup("대전시청")
    assert result["destination"].startswith("대전광역시청 (")


def test_spaced_retry_when_all_candidates_are_shops(naver):
    _calls, _answers, monkeypatch = naver
    monkeypatch.setattr(settings, "naver_search_client_id", "cid")
    monkeypatch.setattr(settings, "naver_search_client_secret", "csecret")
    shops = {
        "items": [
            {
                "title": "양은이네 대전시청점",
                "category": "음식점>한식",
                "roadAddress": "부산광역시 연제구 중앙대로 1001",
            }
        ]
    }
    hall = {
        "items": [
            {
                "title": "대전광역시청",
                "category": "공공,사회기관>특별,광역시청",
                "roadAddress": "부산광역시 연제구 중앙대로 1001",
            }
        ]
    }
    queries = []

    def local(url, params, headers):
        queries.append(params["query"])
        return shops if params["query"] == "대전시청" else hall

    original = service.fetch
    monkeypatch.setattr(
        service, "fetch", lambda u, p, h: local(u, p, h) if "search" in u else original(u, p, h)
    )
    assert service.lookup("대전시청")["destination"].startswith("대전광역시청 (")
    assert queries == ["대전시청", "대전 시청"]
