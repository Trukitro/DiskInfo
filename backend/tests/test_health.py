import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="health.py imports win32com/pythoncom at module level")

from app.health import _parse_smart_temperature


def _fake_smart_blob(attr_id: int, raw_temp_byte: int) -> bytes:
    """Builds a minimal fake VendorSpecific blob: 2-byte header, then one
    12-byte attribute record (id at offset 0, raw value's first byte at
    offset 5) placed at the first attribute slot."""
    blob = bytearray(512)
    offset = 2
    blob[offset] = attr_id
    blob[offset + 5] = raw_temp_byte
    return bytes(blob)


def test_parses_attribute_194():
    assert _parse_smart_temperature(_fake_smart_blob(194, 37)) == 37


def test_falls_back_to_attribute_190_when_194_absent():
    assert _parse_smart_temperature(_fake_smart_blob(190, 42)) == 42


def test_returns_none_when_no_temperature_attribute_present():
    # attribute 9 is Power-On Hours, not a temperature attribute
    assert _parse_smart_temperature(_fake_smart_blob(9, 100)) is None


def test_returns_none_for_implausible_values():
    assert _parse_smart_temperature(_fake_smart_blob(194, 0)) is None
    assert _parse_smart_temperature(_fake_smart_blob(194, 200)) is None


def test_returns_none_for_truncated_buffer():
    assert _parse_smart_temperature(b"\x00" * 5) is None
