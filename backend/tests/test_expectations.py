from app.expectations import evaluate, expected_floor_mb_s


def test_hdd_floor_is_low():
    assert expected_floor_mb_s("HDD", "SATA") == 40.0


def test_nvme_ssd_floor_uses_bus_type():
    assert expected_floor_mb_s("NVMe SSD", "NVMe") == 800.0


def test_sata_ssd_floor_uses_bus_type():
    assert expected_floor_mb_s("SATA SSD", "SATA") == 350.0


def test_generic_ssd_falls_back_when_bus_type_unrecognized():
    assert expected_floor_mb_s("SSD", "USB") == 300.0


def test_unknown_media_type_returns_no_floor():
    assert expected_floor_mb_s("Unknown", "Unknown") is None


def test_evaluate_flags_nvme_running_like_sata():
    underperforming, reason = evaluate("NVMe SSD", "NVMe", 350.0)
    assert underperforming is True
    assert "NVMe SSD" in reason
    assert "350" in reason


def test_evaluate_does_not_flag_healthy_nvme():
    underperforming, reason = evaluate("NVMe SSD", "NVMe", 1800.0)
    assert underperforming is False
    assert reason is None


def test_evaluate_does_not_flag_a_normal_hdd():
    underperforming, reason = evaluate("HDD", "SATA", 120.0)
    assert underperforming is False
    assert reason is None


def test_evaluate_handles_unknown_category_without_flagging():
    underperforming, reason = evaluate("Unknown", "Unknown", 5.0)
    assert underperforming is False
    assert reason is None
