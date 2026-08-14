import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="unbuffered I/O via win32file is Windows-specific")

import app.benchmark as benchmark_module
from app.benchmark import _run_unbuffered, run_benchmark


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


def test_run_unbuffered_rejects_chunk_size_not_sector_aligned(tmp_path):
    # 1000 bytes isn't a multiple of the 4096-byte sector alignment --
    # exercised directly since chunk_mb (always a whole number of MB, hence
    # always a multiple of 4096) can never reach this path through the
    # public run_benchmark() API.
    with pytest.raises(OSError):
        list(_run_unbuffered(str(tmp_path / "test.tmp"), 1000, 1, 1, [], []))
