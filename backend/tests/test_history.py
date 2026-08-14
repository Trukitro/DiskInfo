from app.history import get_history, record_run


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
