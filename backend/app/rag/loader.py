"""파일 → 텍스트. 지원: .hwp / .hwpx / .txt / .md"""

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from app.rag.hwp import read_hwp_text

SUPPORTED = {".hwp", ".hwpx", ".txt", ".md"}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _hwpx_paragraph_text(p: ET.Element) -> str:
    """<hp:p> 하나의 글자. 표 안의 문단(중첩된 p)은 따로 처리되므로 건너뜀."""
    parts: list[str] = []

    def visit(el: ET.Element) -> None:
        for child in el:
            name = _local(child.tag)
            if name == "p":
                continue
            if name == "t":
                parts.append("".join(child.itertext()))
            else:
                visit(child)

    visit(p)
    return "".join(parts)


def read_hwpx_text(path: str | Path) -> str:
    lines: list[str] = []
    with zipfile.ZipFile(path) as z:
        sections = sorted(
            (n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n)),
            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[-1]).group(1)),
        )
        for name in sections:
            root = ET.fromstring(z.read(name))
            for el in root.iter():
                if _local(el.tag) == "p":
                    lines.append(_hwpx_paragraph_text(el))
    return "\n".join(lines)


def load_text(path: str | Path) -> str:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".hwp":
        return read_hwp_text(path)
    if ext == ".hwpx":
        return read_hwpx_text(path)
    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    raise ValueError(
        f"지원하지 않는 파일 형식입니다: {path.name} (지원: {', '.join(sorted(SUPPORTED))})"
    )
