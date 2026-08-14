import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="drives.py imports win32com/pythoncom at module level")

from app.drives import _BUS_TYPES, _MEDIA_TYPES, _infer_media_type, _physical_drive_index


def test_infer_media_type_from_model_string():
    assert _infer_media_type("Samsung 970 EVO NVMe", None) == "NVMe SSD"
    assert _infer_media_type("Crucial MX500 SSD", None) == "SSD"
    assert _infer_media_type("WDC WD10EZEX HDD", None) == "HDD"
    assert _infer_media_type("Totally Unknown Model", None) == "Unknown"


def test_infer_media_type_falls_back_to_wmi_hint_when_name_is_uninformative():
    assert _infer_media_type("Totally Unknown Model", "External hard disk media") == "External hard disk media"


def test_physical_drive_index_extracts_trailing_number():
    assert _physical_drive_index(r"\\.\PHYSICALDRIVE2") == "2"
    assert _physical_drive_index(r"\\.\physicaldrive10") == "10"
    assert _physical_drive_index("garbage") is None


def test_bus_type_and_media_type_maps_cover_common_codes():
    assert _BUS_TYPES[11] == "SATA"
    assert _BUS_TYPES[17] == "NVMe"
    assert _BUS_TYPES[7] == "USB"
    assert _MEDIA_TYPES[4] == "SSD"
    assert _MEDIA_TYPES[3] == "HDD"
