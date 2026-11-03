"""HWP(한글 5.x) 본문 텍스트 추출기 — 외부 라이브러리 없이 표준 라이브러리만 사용.

HWP 파일은 OLE 복합문서 안에 BodyText/Section0, Section1 … 스트림이 있고,
각 스트림은 (압축된) 레코드 목록입니다. 그중 PARA_TEXT(태그 67) 레코드가 문단 글자입니다.

한계: 표는 칸 단위 문단으로 흩어져 나와 구조(행·열)가 사라집니다.
      표가 중요한 문서는 한글에서 HWPX 로 저장해서 쓰는 것을 권장합니다 (loader.py 가 HWPX 도 읽음).
"""

import struct
import zlib
from pathlib import Path

_END = 0xFFFFFFFA  # 체인 끝 표시 (이 값 이상이면 특수 값)
_TAG_PARA_TEXT = 67  # HWPTAG_BEGIN(16) + 51


def _read_ole_streams(data: bytes) -> dict[str, bytes]:
    """OLE 복합문서(CFB)에서 모든 스트림을 {경로: 바이트} 로 꺼냅니다."""
    if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ValueError("HWP(OLE) 형식이 아닙니다. HWPX 라면 확장자를 .hwpx 로 바꿔 주세요.")

    sector_size = 1 << struct.unpack_from("<H", data, 0x1E)[0]
    mini_size = 1 << struct.unpack_from("<H", data, 0x20)[0]
    (n_fat, dir_start, _, mini_cutoff, minifat_start, n_minifat, difat_start, n_difat) = (
        struct.unpack_from("<8I", data, 0x2C)
    )

    def sector(i: int) -> bytes:
        off = 512 + i * sector_size
        return data[off : off + sector_size]

    per_sector = sector_size // 4
    difat = list(struct.unpack_from("<109I", data, 0x4C))
    s = difat_start
    for _ in range(n_difat):
        entries = struct.unpack(f"<{per_sector}I", sector(s))
        difat += entries[:-1]
        s = entries[-1]

    fat: list[int] = []
    for fs in difat[:n_fat]:
        fat += struct.unpack(f"<{per_sector}I", sector(fs))

    def chain(start: int, table: list[int]) -> list[int]:
        out = []
        while start < _END and len(out) <= len(table):
            out.append(start)
            start = table[start]
        return out

    def read_chain(start: int) -> bytes:
        return b"".join(sector(i) for i in chain(start, fat))

    dir_data = read_chain(dir_start)
    entries = []
    for i in range(len(dir_data) // 128):
        e = dir_data[i * 128 : (i + 1) * 128]
        name_len = struct.unpack_from("<H", e, 64)[0]
        left, right, child = struct.unpack_from("<3I", e, 68)
        start, size = struct.unpack_from("<IQ", e, 116)
        entries.append(
            {
                "name": e[: max(name_len - 2, 0)].decode("utf-16le", "replace"),
                "type": e[66],  # 1=storage, 2=stream, 5=root
                "left": left,
                "right": right,
                "child": child,
                "start": start,
                "size": size & 0xFFFFFFFF,
            }
        )

    root = entries[0]
    mini_stream = read_chain(root["start"]) if root["start"] < _END else b""
    minifat: list[int] = []
    if n_minifat:
        raw = read_chain(minifat_start)
        minifat = list(struct.unpack(f"<{len(raw) // 4}I", raw))

    def stream_bytes(e: dict) -> bytes:
        if e["size"] < mini_cutoff:
            parts = (
                mini_stream[i * mini_size : (i + 1) * mini_size] for i in chain(e["start"], minifat)
            )
            return b"".join(parts)[: e["size"]]
        return read_chain(e["start"])[: e["size"]]

    streams: dict[str, bytes] = {}

    def walk(idx: int, prefix: str) -> None:
        if idx >= len(entries):
            return
        e = entries[idx]
        walk(e["left"], prefix)
        walk(e["right"], prefix)
        path = prefix + e["name"]
        if e["type"] == 2:
            streams[path] = stream_bytes(e)
        elif e["type"] == 1:
            walk(e["child"], path + "/")

    walk(root["child"], "")
    return streams


def _para_texts(buf: bytes):
    """섹션 레코드에서 문단 텍스트를 하나씩 꺼냅니다."""
    i = 0
    while i + 4 <= len(buf):
        header = struct.unpack_from("<I", buf, i)[0]
        i += 4
        tag, size = header & 0x3FF, (header >> 20) & 0xFFF
        if size == 0xFFF:
            size = struct.unpack_from("<I", buf, i)[0]
            i += 4
        record = buf[i : i + size]
        i += size
        if tag != _TAG_PARA_TEXT:
            continue

        out, j = [], 0
        while j + 2 <= len(record):
            ch = struct.unpack_from("<H", record, j)[0]
            if ch < 32:
                if ch == 9:  # 탭
                    out.append(b"\t\x00")
                # 문자형 컨트롤(0,10,13,24~31)은 2바이트, 나머지 컨트롤은 16바이트
                j += 2 if (ch in (0, 10, 13) or 24 <= ch <= 31) else 16
            else:
                out.append(record[j : j + 2])
                j += 2
        yield b"".join(out).decode("utf-16le", "replace")


def read_hwp_text(path: str | Path) -> str:
    """HWP 파일 → 문단을 줄바꿈으로 이은 텍스트."""
    streams = _read_ole_streams(Path(path).read_bytes())
    if "FileHeader" not in streams:
        raise ValueError("HWP 파일 헤더를 찾을 수 없습니다.")
    header = streams["FileHeader"]
    if header[36] & 0x02:
        raise ValueError("암호가 걸린 HWP 파일은 읽을 수 없습니다.")
    compressed = bool(header[36] & 0x01)

    sections = sorted(
        (k for k in streams if k.startswith("BodyText/Section")),
        key=lambda k: int(k.removeprefix("BodyText/Section")),
    )
    lines: list[str] = []
    for key in sections:
        buf = streams[key]
        if compressed:
            buf = zlib.decompress(buf, -15)
        lines.extend(_para_texts(buf))
    return "\n".join(lines)
