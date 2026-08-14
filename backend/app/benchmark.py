"""Sequential read/write throughput test for a mounted drive. A generator
so the FastAPI layer can push each chunk's instantaneous speed over the
WebSocket as it happens, instead of blocking on one big transfer like the
original DiskInfov5 desktop app's benchmark_drive() did -- which also only
moved 10MB total, too little to get a stable reading past filesystem
overhead.

Known caveat (inherited from the original implementation, not new here):
the write phase uses buffered I/O, so the read phase that immediately
follows can be served from Windows' page cache instead of the physical
media -- read numbers on fast/lightly-loaded systems can come back far
above what the drive can actually sustain. Fixing this properly needs
FILE_FLAG_NO_BUFFERING (via win32file, with sector-aligned buffers), which
was judged too much untested low-level Windows API surface to add to a
disk tool without hardware to validate it against; write speed is the more
trustworthy of the two numbers until that lands."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

_CHUNK_MB = 10
_TOTAL_MB = 200
_TEST_FILENAME = "diskinfo_benchmark.tmp"


def run_benchmark(mountpoint: str, total_mb: int = _TOTAL_MB, chunk_mb: int = _CHUNK_MB) -> Iterator[dict]:
    test_path = os.path.join(mountpoint, _TEST_FILENAME)
    chunk = b"0" * (chunk_mb * 1024 * 1024)
    chunks = max(total_mb // chunk_mb, 1)

    try:
        write_speeds = []
        with open(test_path, "wb") as f:
            for i in range(chunks):
                start = time.perf_counter()
                f.write(chunk)
                f.flush()
                os.fsync(f.fileno())
                elapsed = time.perf_counter() - start
                speed = chunk_mb / elapsed if elapsed > 0 else 0.0
                write_speeds.append(speed)
                yield {"phase": "write", "chunk": i + 1, "of": chunks, "speed_mb_s": round(speed, 1)}

        read_speeds = []
        with open(test_path, "rb") as f:
            for i in range(chunks):
                start = time.perf_counter()
                data = f.read(chunk_mb * 1024 * 1024)
                elapsed = time.perf_counter() - start
                if not data:
                    break
                speed = chunk_mb / elapsed if elapsed > 0 else 0.0
                read_speeds.append(speed)
                yield {"phase": "read", "chunk": i + 1, "of": chunks, "speed_mb_s": round(speed, 1)}

        yield {
            "phase": "done",
            "write_avg_mb_s": round(sum(write_speeds) / len(write_speeds), 1) if write_speeds else 0,
            "read_avg_mb_s": round(sum(read_speeds) / len(read_speeds), 1) if read_speeds else 0,
        }
    except OSError as exc:
        yield {"phase": "error", "message": str(exc)}
    finally:
        if os.path.exists(test_path):
            try:
                os.remove(test_path)
            except OSError:
                pass
