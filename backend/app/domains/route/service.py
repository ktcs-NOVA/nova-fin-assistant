"""경로 조회 (U-05 출장비 계산): 근무지(공사 본사) → 도착지 자동차 길 찾기 거리.

자가용 출장의 운행거리는 '사무실(근무지) → 출장지, 네이버 길찾기 km' 기준입니다 (precheck/rules.py).
화면은 이 편도 거리를 받아 자가용이면 왕복으로 운행거리를 채웁니다.

부르는 API (네이버 클라우드 플랫폼 Maps, 키는 서버에만 둠)
    1. Geocoding     주소 → 좌표        GET {base}/map-geocode/v2/geocode?query=주소
    2. Directions 5  좌표 → 자동차 경로  GET {base}/map-direction/v1/driving?start=경도,위도&goal=경도,위도
    인증 헤더: x-ncp-apigw-api-key-id (Client ID), x-ncp-apigw-api-key (Client Secret)
    콘솔에서 Application 에 두 API 를 모두 선택해야 함 (안 하면 429)

Geocoding 은 '주소'만 찾습니다. "부산시청" 같은 장소 이름이 안 찾아지면, NAVER API HUB 의 지역 검색 키가 있을 때만
장소 이름 → 도로명 주소로 바꿔 한 번 더 찾습니다.
    3. 지역 검색   GET https://naverapihub.apigw.ntruss.com/search/v1/local?query=장소&display=1
    (예전 개발자센터 openapi.naver.com 검색 API 는 NAVER API HUB 로 옮겨졌고, 예전 키는 쓸 수 없음.
     인증 헤더는 Maps 와 같은 이름이지만 NAVER API HUB 에서 따로 받은 Client ID / Secret 을 씀. 하루 25,000회)
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.errors import AppError

log = logging.getLogger("nova.route")

LOCAL_SEARCH_URL = "https://naverapihub.apigw.ntruss.com/search/v1/local"
TIMEOUT = 8.0  # 초

NOT_CONFIGURED = "경로 조회가 아직 설정되지 않았어요. 거리(km)는 직접 입력해 주세요."
NOT_FOUND = "도착지를 찾지 못했어요. 도로명 주소(예: 부산광역시 중구 중앙대로 120)로 다시 찾거나 거리(km)를 직접 입력해 주세요."
KEY_ERROR = "네이버 지도 API 키를 확인해 주세요. 거리(km)는 직접 입력할 수 있어요."
QUOTA_ERROR = "네이버 지도 API 사용 한도를 넘었거나, 콘솔에서 Geocoding·Directions 5 를 선택하지 않았어요. 거리(km)는 직접 입력해 주세요."
UNREACHABLE = (
    "네이버 지도 API 에 연결하지 못했어요. 잠시 후 다시 시도하거나 거리(km)를 직접 입력해 주세요."
)

# Directions 5 응답 code: 0 성공, 1 출발지=도착지, 2 출발지·도착지가 도로 주변이 아님, 3 자동차 길 없음
_DIRECTIONS_ERRORS = {
    1: "도착지가 근무지와 같은 곳이에요.",
    2: "도착지 근처에서 도로를 찾지 못했어요. 주소를 조금 더 정확히 적어 주세요.",
    3: "자동차로 갈 수 있는 길을 찾지 못했어요.",
}


@dataclass
class Point:
    lng: str  # 경도 (x)
    lat: str  # 위도 (y)
    address: str


# 바깥 API 호출 한 군데. 테스트에서는 가짜 함수로 바꿔 끼웁니다.
Fetch = Callable[[str, dict, dict], dict]


def _fetch(url: str, params: dict, headers: dict) -> dict:
    try:
        res = httpx.get(url, params=params, headers=headers, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        log.warning("경로 API 연결 실패 %s: %s", url, e)
        raise AppError(UNREACHABLE, 502) from e
    if res.status_code in (401, 403):
        log.warning("경로 API 인증 실패 %s → %s", url, res.status_code)
        raise AppError(KEY_ERROR, 502)
    if res.status_code == 429:
        raise AppError(QUOTA_ERROR, 502)
    if res.status_code >= 400:
        log.warning("경로 API 오류 %s → %s %s", url, res.status_code, res.text[:200])
        raise AppError(
            f"네이버 지도 API 오류(HTTP {res.status_code}). 거리(km)는 직접 입력해 주세요.", 502
        )
    return res.json()


fetch: Fetch = _fetch


def _maps_headers() -> dict:
    return {
        "x-ncp-apigw-api-key-id": settings.naver_maps_client_id.strip(),
        "x-ncp-apigw-api-key": settings.naver_maps_client_secret.strip(),
        "Accept": "application/json",
    }


def geocode(query: str) -> Point | None:
    data = fetch(
        f"{settings.naver_maps_base}/map-geocode/v2/geocode", {"query": query}, _maps_headers()
    )
    found = data.get("addresses") or []
    if not found:
        return None
    a = found[0]
    return Point(str(a["x"]), str(a["y"]), a.get("roadAddress") or a.get("jibunAddress") or query)


def place_address(name: str) -> tuple[str, str] | None:
    """장소 이름 → (장소 이름, 주소). NAVER API HUB 키가 없거나 못 찾으면 None.

    응답의 mapx·mapy 좌표는 형식이 문서에 분명하지 않아 쓰지 않고, 주소를 다시 Geocoding 합니다.
    """
    cid, secret = (
        settings.naver_search_client_id.strip(),
        settings.naver_search_client_secret.strip(),
    )
    if not (cid and secret):
        return None
    headers = {
        "x-ncp-apigw-api-key-id": cid,
        "x-ncp-apigw-api-key": secret,
        "Accept": "application/json",
    }

    def candidates(query: str) -> list[dict]:
        data = fetch(LOCAL_SEARCH_URL, {"query": query, "display": 5}, headers)
        return [i for i in data.get("items") or [] if i.get("roadAddress") or i.get("address")]

    items = candidates(name)
    # 후보가 전부 가게·지점이면 ("대전시청" → "○○ 대전시청점" 5개) 띄어 써서 한 번 더 ("대전 시청")
    spaced = _spaced(name)
    if spaced and (not items or min(map(_place_rank, items)) > 0):
        items = items + candidates(spaced)
    if not items:
        return None
    best = min(items, key=_place_rank)  # 같은 순위면 앞의 것 (네이버가 준 순서)
    return _plain(best.get("title") or name), best.get("roadAddress") or best.get("address")


# "대전시청" → "대전 시청". 붙여 쓰면 지점 이름("대전시청점")과 더 잘 맞아 버림
_PLACE_SUFFIX = re.compile(r"^(\S+?)(시청|구청|군청|도청|청사|역|공항|터미널)$")


def _spaced(name: str) -> str | None:
    m = _PLACE_SUFFIX.match(name.strip())
    return f"{m[1]} {m[2]}" if m else None


# 출장지는 대개 기관·역·시설. "대전시청" 검색에 "○○숯불구이 대전시청점"이 먼저 오는 일이 있어
# 음식점·카페·상점 같은 업종과 "○○점" 지점은 뒤로 미룹니다.
_SHOP_CATEGORIES = (
    "음식점",
    "한식",
    "중식",
    "일식",
    "양식",
    "카페",
    "디저트",
    "술집",
    "쇼핑",
    "생활",
    "미용",
)


def _plain(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)  # 검색어 강조 태그(<b>) 제거


def _place_rank(item: dict) -> int:
    category = item.get("category") or ""
    rank = 2 if any(c in category for c in _SHOP_CATEGORIES) else 0
    if _plain(item.get("title") or "").endswith("점"):
        rank += 1
    return rank


_origin: Point | None = None
_cache: dict[str, dict] = {}  # 같은 도착지는 다시 부르지 않음 (무료 사용량 아끼기)


def _origin_point() -> Point:
    global _origin
    if _origin is None:
        _origin = geocode(settings.route_origin_address)
        if _origin is None:
            raise AppError(
                "근무지 주소의 위치를 찾지 못했어요. backend/.env 의 ROUTE_ORIGIN_ADDRESS 를 확인해 주세요.",
                502,
            )
    return _origin


def lookup(destination: str) -> dict:
    """근무지 → 도착지: { destination, distance_km(편도), duration_min }"""
    query = " ".join((destination or "").split())
    if not query:
        raise AppError("도착지를 입력해 주세요.")
    if not settings.route_enabled:
        raise AppError(NOT_CONFIGURED, 503)
    if query in _cache:
        return _cache[query]

    label = None
    goal = geocode(query)
    if goal is None:  # 주소가 아니라 장소 이름일 수 있음
        place = place_address(query)
        if place:
            label, address = place
            goal = geocode(address)
    if goal is None:
        raise AppError(NOT_FOUND, 404)

    start = _origin_point()
    data = fetch(
        f"{settings.naver_maps_base}/map-direction/v1/driving",
        {"start": f"{start.lng},{start.lat}", "goal": f"{goal.lng},{goal.lat}"},
        _maps_headers(),
    )
    code = data.get("code")
    if code != 0:
        raise AppError(
            _DIRECTIONS_ERRORS.get(code, data.get("message") or "경로를 찾지 못했어요."), 404
        )
    summary = data["route"]["traoptimal"][0]["summary"]  # 실시간 빠른 길

    result = {
        "destination": f"{label} ({goal.address})" if label else goal.address,
        "distance_km": round(summary["distance"] / 1000, 1),  # m → km, 편도
        "duration_min": round(summary["duration"] / 60000),  # ms → 분
    }
    _cache[query] = result
    return result


def reset_cache() -> None:
    """테스트용: 근무지 좌표와 조회 결과 기억을 지웁니다."""
    global _origin
    _origin = None
    _cache.clear()
