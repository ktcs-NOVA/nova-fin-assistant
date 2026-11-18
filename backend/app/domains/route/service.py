"""경로 조회: 회사(본사) → 도착지의 자동차 길 찾기 거리. 출장비 계산의 자가용 운행거리에 씁니다.

네이버 클라우드 플랫폼 Maps API 를 서버에서 부릅니다 (키를 브라우저에 내보내지 않기 위해).
    Geocoding      주소 → 좌표          GET {MAPS}/map-geocode/v2/geocode?query=
    Directions 5   좌표 → 자동차 경로   GET {MAPS}/map-direction/v1/driving?start=경도,위도&goal=경도,위도
    (인증 헤더: x-ncp-apigw-api-key-id / x-ncp-apigw-api-key — 콘솔에서 Application 을 등록하고 두 API 를 선택해야 함)

Geocoding 은 "주소"를 받습니다. "부산시청" 같은 장소 이름은 못 찾을 수 있어서, 네이버 검색(지역) 키가 있으면
장소 이름 → 도로명 주소로 한 번 바꾼 뒤 다시 좌표를 찾습니다 (없으면 이 단계는 건너뜀).

키가 없으면 503 으로 "설정되지 않았다"고 알려 주고, 화면은 거리를 직접 입력하게 안내합니다.
"""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import settings
from app.core.errors import AppError

log = logging.getLogger("nova.route")

MAPS = "https://maps.apigw.ntruss.com"
LOCAL_SEARCH = "https://openapi.naver.com/v1/search/local.json"
TIMEOUT = 8  # 초

NOT_CONFIGURED = "경로 조회가 아직 설정되지 않았어요. 거리(km)는 직접 입력해 주세요."
NOT_FOUND = "도착지를 찾지 못했습니다. 도로명 주소로 다시 검색하거나 거리(km)를 직접 입력해 주세요."

# Directions 5 응답 code (0 이 성공)
_ROUTE_ERRORS = {
    1: "도착지가 회사와 같은 곳입니다.",
    2: "도착지가 도로 주변이 아니어서 경로를 찾지 못했습니다. 주소를 조금 더 정확히 적어 주세요.",
    3: "자동차로 가는 경로를 찾지 못했습니다.",
}

_cache: dict[str, dict] = {}  # 도착지 → 결과 (같은 곳을 다시 물으면 API 를 다시 부르지 않음)
_origin: tuple[str, str] | None = None  # 회사 좌표 (경도, 위도)


def configured() -> bool:
    return bool(settings.naver_maps_key_id.strip() and settings.naver_maps_key.strip())


def _get_json(url: str, headers: dict[str, str]) -> dict:
    """GET → JSON. 네트워크·인증 오류는 화면에 보여 줄 수 있는 문장으로 바꿉니다."""
    req = urllib.request.Request(url, headers={"Accept": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:  # 고정된 https 주소만 부름
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log.warning("경로 API %s → HTTP %s", url.split("?")[0], e.code)
        if e.code in (401, 403):
            raise AppError("네이버 지도 API 키가 올바르지 않아 경로를 조회하지 못했어요. 거리(km)는 직접 입력해 주세요.", 502) from e
        if e.code == 429:
            raise AppError("네이버 지도 API 사용 한도를 넘었거나 사용 신청이 안 된 API 예요. 거리(km)는 직접 입력해 주세요.", 502) from e
        raise AppError(f"네이버 지도 API 오류 (HTTP {e.code})", 502) from e
    except (urllib.error.URLError, TimeoutError) as e:
        log.warning("경로 API %s 연결 실패: %s", url.split("?")[0], e)
        raise AppError("네이버 지도 API 에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", 502) from e


def _maps_headers() -> dict[str, str]:
    return {"x-ncp-apigw-api-key-id": settings.naver_maps_key_id.strip(), "x-ncp-apigw-api-key": settings.naver_maps_key.strip()}


def _geocode(query: str) -> tuple[str, str, str] | None:
    """주소 → (경도, 위도, 찾은 주소). 못 찾으면 None."""
    url = f"{MAPS}/map-geocode/v2/geocode?{urllib.parse.urlencode({'query': query})}"
    found = _get_json(url, _maps_headers()).get("addresses") or []
    if not found:
        return None
    a = found[0]
    return str(a["x"]), str(a["y"]), a.get("roadAddress") or a.get("jibunAddress") or query


def _place_address(name: str) -> tuple[str, str] | None:
    """장소 이름 → (장소 이름, 주소). 네이버 검색(지역) 키가 없거나 못 찾으면 None."""
    cid, secret = settings.naver_search_client_id.strip(), settings.naver_search_client_secret.strip()
    if not (cid and secret):
        return None
    url = f"{LOCAL_SEARCH}?{urllib.parse.urlencode({'query': name, 'display': 1})}"
    items = _get_json(url, {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret}).get("items") or []
    if not items:
        return None
    title = re.sub(r"<[^>]+>", "", items[0].get("title") or name)  # 검색어 강조 태그 제거
    address = items[0].get("roadAddress") or items[0].get("address")
    return (title, address) if address else None


def _origin_point() -> tuple[str, str]:
    global _origin
    if _origin is None:
        hit = _geocode(settings.route_origin_address)
        if hit is None:
            raise AppError("회사 주소의 좌표를 찾지 못했습니다. backend/.env 의 ROUTE_ORIGIN_ADDRESS 를 확인해 주세요.", 502)
        _origin = hit[0], hit[1]
    return _origin


def lookup(destination: str) -> dict:
    """회사 → 도착지: { destination, distance_km(편도), duration_min }."""
    query = " ".join((destination or "").split())
    if not query:
        raise AppError("도착지를 입력해 주세요.")
    if not configured():
        log.warning("경로 조회 키 없음 — backend/.env 의 NAVER_MAPS_KEY_ID · NAVER_MAPS_KEY 를 넣어 주세요")
        raise AppError(NOT_CONFIGURED, 503)
    if query in _cache:
        return _cache[query]

    place_name = None
    hit = _geocode(query)
    if hit is None:  # 주소가 아니라 장소 이름일 수 있음
        place = _place_address(query)
        if place is not None:
            place_name = place[0]
            hit = _geocode(place[1])
    if hit is None:
        raise AppError(NOT_FOUND, 404)
    lng, lat, address = hit

    start = ",".join(_origin_point())
    url = f"{MAPS}/map-direction/v1/driving?{urllib.parse.urlencode({'start': start, 'goal': f'{lng},{lat}'})}"
    data = _get_json(url, _maps_headers())
    code = data.get("code")
    if code != 0:
        raise AppError(_ROUTE_ERRORS.get(code, data.get("message") or "경로를 찾지 못했습니다."), 404 if code in _ROUTE_ERRORS else 502)
    summary = data["route"]["traoptimal"][0]["summary"]

    result = {
        "destination": f"{place_name} ({address})" if place_name else address,
        "distance_km": round(summary["distance"] / 1000, 1),  # 미터 → km (편도)
        "duration_min": round(summary["duration"] / 60000),  # 밀리초 → 분
    }
    _cache[query] = result
    return result
