from app.history import get_health_history, get_history, record_health_snapshot, record_run


def test_record_and_get_history_filters_by_drive(history_path):
    record_run("C", 120.5, 480.2, 200, True, path=history_path)
    record_run("C", 100.0, 400.0, 200, False, path=history_path)
    record_run("D", 50.0, 60.0, 50, True, path=history_path)

    c_runs = get_history(drive="C", path=history_path)
    assert len(c_runs) == 2
    assert c_runs[0]["write_avg_mb_s"] == 100.0  # most recent first (DESC by ts)
    assert all(r["drive"] == "C" for r in c_runs)

    all_runs = get_history(path=history_path)
    assert len(all_runs) == 3


def test_get_history_empty_db_returns_empty_list(history_path):
    assert get_history(path=history_path) == []


def test_cache_bypassed_roundtrips_as_bool(history_path):
    record_run("C", 1.0, 2.0, 10, False, path=history_path)
    row = get_history(drive="C", path=history_path)[0]
    assert row["cache_bypassed"] is False


def test_iops_and_underperforming_fields_roundtrip(history_path):
    record_run(
        "C",
        350.0,
        400.0,
        200,
        True,
        iops_write=12000.0,
        iops_read=15000.0,
        avg_latency_write_ms=0.083,
        avg_latency_read_ms=0.067,
        underperforming=True,
        underperforming_reason="NVMe SSD over NVMe wrote at 350 MB/s, below the ~800 MB/s expected...",
        path=history_path,
    )
    row = get_history(drive="C", path=history_path)[0]
    assert row["iops_write"] == 12000.0
    assert row["iops_read"] == 15000.0
    assert row["avg_latency_write_ms"] == 0.083
    assert row["underperforming"] is True
    assert "NVMe" in row["underperforming_reason"]


def test_optional_fields_default_to_none(history_path):
    record_run("C", 100.0, 100.0, 200, True, path=history_path)
    row = get_history(drive="C", path=history_path)[0]
    assert row["iops_write"] is None
    assert row["underperforming"] is None
    assert row["underperforming_reason"] is None


def test_health_snapshots_roundtrip_in_chronological_order(history_path):
    record_health_snapshot("\\\\.\\PHYSICALDRIVE0", 35, 100, False, path=history_path)
    record_health_snapshot("\\\\.\\PHYSICALDRIVE0", 37, 100, False, path=history_path)
    record_health_snapshot("\\\\.\\PHYSICALDRIVE1", 50, 60, True, path=history_path)

    rows = get_health_history("\\\\.\\PHYSICALDRIVE0", path=history_path)
    assert len(rows) == 2
    assert [r["temperature_c"] for r in rows] == [35, 37]  # oldest first, unlike benchmark history
    assert all(r["predicted_failure"] is False for r in rows)


def test_health_snapshots_null_temperature_roundtrips(history_path):
    record_health_snapshot("\\\\.\\PHYSICALDRIVE0", None, 100, False, path=history_path)
    row = get_health_history("\\\\.\\PHYSICALDRIVE0", path=history_path)[0]
    assert row["temperature_c"] is None


def test_get_health_history_empty_returns_empty_list(history_path):
    assert get_health_history("\\\\.\\PHYSICALDRIVE0", path=history_path) == []
