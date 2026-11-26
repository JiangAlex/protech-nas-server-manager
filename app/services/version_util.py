"""Version numbers "major.minor.patch" (ESP32 firmware)."""

import re
from typing import Optional

SEMVER_RE = re.compile(r"^(\d{1,4})\.(\d{1,4})\.(\d{1,4})$")


def parse(version: Optional[str]) -> Optional[tuple[int, int, int]]:
    """(major, minor, patch), or None when the text is not exactly "x.y.z"."""
    m = SEMVER_RE.match((version or "").strip())
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def is_newer(candidate: str, current: Optional[str]) -> bool:
    """True when `candidate` should replace `current`.

    A device on an unknown or unparsable version gets the release. A device on the same or a newer
    version gets nothing, so a device ahead of the release record is never sent back to it.
    """
    c = parse(candidate)
    if c is None:
        return False
    cur = parse(current)
    return cur is None or c > cur
