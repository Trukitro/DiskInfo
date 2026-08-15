import sys

import pytest

from app.health import _parse_smart_attributes, _parse_smart_temperature, _tbw_from_attrs

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="health.py imports win32com/pythoncom at module level")


def _fake_smart_blob(attr_id: int, raw_temp_byte: int) -> bytes:
    """Builds a minimal fake VendorSpecific blob: 2-byte header, then one
    12-byte attribute record (id at offset 0, raw value's first byte at
    offset 5) placed at the first attribute slot."""
    blob = bytearray(512)
    offset = 2
    blob[offset] = attr_id
    blob[offset + 5] = raw_temp_byte
    return bytes(blob)


def _fake_multi_attr_blob(entries: dict[int, int]) -> bytes:
    """Same layout as _fake_smart_blob but places multiple attribute
    records (id -> 6-byte little-endian raw value) at successive slots."""
    blob = bytearray(512)
    for i, (attr_id, raw_value) in enumerate(entries.items()):
        offset = 2 + i * 12
        blob[offset] = attr_id
        blob[offset + 5 : offset + 11] = raw_value.to_bytes(6, "little")
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


def test_parse_smart_attributes_returns_current_worst_raw():
    blob = _fake_multi_attr_blob({194: 37, 9: 12000})
    attrs = _parse_smart_attributes(blob)
    assert attrs[194]["raw"] == 37
    assert attrs[9]["raw"] == 12000
    assert 194 in attrs and 9 in attrs


def test_parse_smart_attributes_skips_zero_id_slots():
    blob = _fake_multi_attr_blob({194: 37})
    attrs = _parse_smart_attributes(blob)
    assert list(attrs.keys()) == [194]


def test_tbw_estimate_converts_lbas_to_gb():
    # 241 = Total_LBAs_Written; 1 GiB of LBAs at 512 bytes/LBA = 2097152 LBAs
    blob = _fake_multi_attr_blob({241: 2097152})
    attrs = _parse_smart_attributes(blob)
    assert _tbw_from_attrs(attrs) == 1.0


def test_tbw_estimate_none_when_attribute_absent():
    blob = _fake_multi_attr_blob({194: 37})
    attrs = _parse_smart_attributes(blob)
    assert _tbw_from_attrs(attrs) is None


def test_tbw_estimate_none_when_raw_is_zero():
    blob = _fake_multi_attr_blob({241: 0})
    attrs = _parse_smart_attributes(blob)
    assert _tbw_from_attrs(attrs) is None
