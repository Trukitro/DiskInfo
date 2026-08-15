import sys

import pytest

import app.benchmark as benchmark_module
from app.benchmark import _run_iops, _run_unbuffered, run_benchmark

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="unbuffered I/O via win32file is Windows-specific")


def test_run_benchmark_produces_expected_event_sequence(tmp_path):
    events = list(run_benchmark(str(tmp_path) + "\\", total_mb=20, chunk_mb=10))

    write_events = [e for e in events if e["phase"] == "write"]
    read_events = [e for e in events if e["phase"] == "read"]
    assert len(write_events) == 2
    assert len(read_events) == 2
    assert events[-1]["phase"] == "done"

    done = events[-1]
    assert done["write_avg_mb_s"] > 0
    assert done["read_avg_mb_s"] > 0
    assert isinstance(done["cache_bypassed"], bool)


def test_run_benchmark_includes_iops_phase_when_cache_bypassed(tmp_path):
    events = list(run_benchmark(str(tmp_path) + "\\", total_mb=20, chunk_mb=10))

    assert any(e["phase"] == "iops_write" for e in events)
    assert any(e["phase"] == "iops_read" for e in events)

    done = events[-1]
    assert done["cache_bypassed"] is True
    assert done["iops_write"] > 0
    assert done["iops_read"] > 0
    assert done["avg_latency_write_ms"] > 0
    assert done["avg_latency_read_ms"] > 0


def test_run_benchmark_skips_iops_phase_on_buffered_fallback(tmp_path, monkeypatch):
    def _reject_no_buffering(*args, **kwargs):
        raise OSError("simulated: this filesystem rejects FILE_FLAG_NO_BUFFERING")

    monkeypatch.setattr(benchmark_module.win32file, "CreateFile", _reject_no_buffering)

    events = list(run_benchmark(str(tmp_path) + "\\", total_mb=10, chunk_mb=10))

    assert not any(e["phase"] in ("iops_write", "iops_read") for e in events)
    done = events[-1]
    assert done["iops_write"] is None
    assert done["iops_read"] is None
    assert done["avg_latency_write_ms"] is None
    assert done["avg_latency_read_ms"] is None


def test_run_benchmark_reports_fallback_message_when_only_iops_phase_fails(tmp_path, monkeypatch):
    # Isolates a failure to just the IOPS phase (SetFilePointer is only used
    # there) so the sequential result still comes back intact -- the IOPS
    # test failing shouldn't take down the whole benchmark.
    def _reject_seek(*args, **kwargs):
        raise OSError("simulated: seek failed")

    monkeypatch.setattr(benchmark_module.win32file, "SetFilePointer", _reject_seek)

    events = list(run_benchmark(str(tmp_path) + "\\", total_mb=20, chunk_mb=10))

    assert any(e["phase"] == "fallback" and "IOPS" in e["message"] for e in events)
    done = events[-1]
    assert done["cache_bypassed"] is True  # sequential phase was unaffected
    assert done["write_avg_mb_s"] > 0
    assert done["iops_write"] is None


def test_run_benchmark_cleans_up_temp_file(tmp_path):
    list(run_benchmark(str(tmp_path) + "\\", total_mb=10, chunk_mb=10))
    assert not (tmp_path / "diskinfo_benchmark.tmp").exists()


def test_run_benchmark_falls_back_when_unbuffered_io_unavailable(tmp_path, monkeypatch):
    def _reject_no_buffering(*args, **kwargs):
        raise OSError("simulated: this filesystem rejects FILE_FLAG_NO_BUFFERING")

    monkeypatch.setattr(benchmark_module.win32file, "CreateFile", _reject_no_buffering)

    events = list(run_benchmark(str(tmp_path) + "\\", total_mb=10, chunk_mb=10))

    assert any(e["phase"] == "fallback" for e in events)
    assert any(e["phase"] == "write" for e in events)
    assert any(e["phase"] == "read" for e in events)
    assert events[-1]["phase"] == "done"
    assert events[-1]["cache_bypassed"] is False


def test_run_iops_directly_produces_latencies(tmp_path):
    test_path = str(tmp_path / "iops_test.tmp")
    # _run_iops expects the file to already exist with data (as it would
    # after the sequential write phase) -- pre-create it here since this
    # test calls _run_iops in isolation.
    with open(test_path, "wb") as f:
        f.write(b"0" * (1024 * 1024))

    write_latencies: list[float] = []
    read_latencies: list[float] = []
    list(_run_iops(test_path, 1024 * 1024, write_latencies, read_latencies))

    assert len(write_latencies) == benchmark_module._IOPS_OPS
    assert len(read_latencies) == benchmark_module._IOPS_OPS
    assert all(latency >= 0 for latency in write_latencies + read_latencies)


def test_run_unbuffered_rejects_chunk_size_not_sector_aligned(tmp_path):
    # 1000 bytes isn't a multiple of the 4096-byte sector alignment --
    # exercised directly since chunk_mb (always a whole number of MB, hence
    # always a multiple of 4096) can never reach this path through the
    # public run_benchmark() API.
    with pytest.raises(OSError):
        list(_run_unbuffered(str(tmp_path / "test.tmp"), 1000, 1, 1, [], []))
