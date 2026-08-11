"""Versi aplikasi ZFace Desktop + pembanding versi semver sederhana.

Dijaga sinkron dengan tag rilis GitHub (vX.Y.Z).
"""
VERSION = "0.3.0"
REPO = "djvpri/zface-desktop"


def _parse(v: str):
    """'v0.2.0' atau '0.2.0' -> (0, 2, 0). Non-numerik -> None."""
    s = v.strip().lstrip("v").split(".")
    try:
        return tuple(int(x) for x in s)
    except ValueError:
        return None


def compare_versions(a: str, b: str) -> int:
    """-1 jika a < b, 0 jika sama/ tak-parseable, 1 jika a > b."""
    pa, pb = _parse(a), _parse(b)
    if pa is None or pb is None:
        return 0
    return (pa > pb) - (pa < pb)
