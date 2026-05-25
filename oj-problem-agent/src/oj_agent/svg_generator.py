from __future__ import annotations

import xml.etree.ElementTree as ET


def is_valid_svg(svg: str) -> bool:
    if not svg.strip():
        return False
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return False
    tag = root.tag.split("}", 1)[-1].lower()
    return tag == "svg"
