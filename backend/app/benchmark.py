"""Sequential read/write throughput test for a mounted drive. A generator
so the FastAPI layer can push each chunk's instantaneous speed over the
WebSocket as it happens, instead of blocking on one big transfer like the
original DiskInfov5 desktop app's benchmark_drive() did -- which also only
moved 10MB total, too little to get a stable reading past filesystem
overhead.

Measures with FILE_FLAG_NO_BUFFERING so both phases bypass Windows' page
cache and hit the physical drive -- without it, the read phase that
immediately follows the write phase can be served from RAM instead of the
disk (a mechanical HDD was observed reporting >3000 MB/s "read" with plain
buffered I/O). Unbuffered I/O requires the buffer address, transfer size,
and file offset all be sector-aligned; `mmap.mmap(-1, size)` gives
page-aligned (4096-byte) memory for free on Windows, which covers both
512e and 4Kn drives without manual `ctypes` alignment.

If unbuffered I/O isn't available for some reason (an unusual filesystem,
a virtual disk that rejects the flag), falls back to plain buffered I/O
and reports `cache_bypassed: false` on the `done` event rather than
silently trusting a number that might be inflated."""

from __future__ import annotations

import mmap
import os
import random
import time
from collections.abc import Iterator

import pywintypes
import win32file

_CHUNK_MB = 10
_TOTAL_MB = 200
_TEST_FILENAME = "diskinfo_benchmark.tmp"
_SECTOR_ALIGN = 4096  # covers both 512e and 4Kn drives; also the OS page size
_IOPS_BLOCK_SIZE = 4096  # standard IOPS benchmark block size
_IOPS_OPS = 256


def run_benchmark(mountpoint: str, total_mb: int = _TOTAL_MB, chunk_mb: int = _CHUNK_MB) -> Iterator[dict]:
    test_path = os.path.join(mountpoint, _TEST_FILENAME)
    chunk_bytes = chunk_mb * 1024 * 1024
    chunks = max(total_mb // chunk_mb, 1)
    write_speeds: list[float] = []
    read_speeds: list[float] = []
    write_latencies_ms: list[float] = []
    read_latencies_ms: list[float] = []
    cache_bypassed = True

    try:
        try:
            yield from _run_unbuffered(test_path, chunk_bytes, chunks, chunk_mb, write_speeds, read_speeds)
        except (OSError, pywintypes.error) as exc:
            cache_bypassed = False
            write_speeds.clear()
            read_speeds.clear()
            if os.path.exists(test_path):
                os.remove(test_path)
            yield {"phase": "fallback", "message": f"unbuffered I/O unavailable ({exc}); using buffered I/O"}
            yield from _run_buffered(test_path, chunk_bytes, chunks, chunk_mb, write_speeds, read_speeds)

        if cache_bypassed:
            # Random 4KB IOPS/latency only means anything measured against
            # the physical drive -- skipped on the buffered fallback path,
            # same reasoning as the sequential test: buffered random I/O
            # would just hit the page cache and report meaningless numbers.
            try:
                yield from _run_iops(test_path, chunk_bytes * chunks, write_latencies_ms, read_latencies_ms)
            except (OSError, pywintypes.error) as exc:
                yield {"phase": "fallback", "message": f"IOPS test skipped ({exc})"}

        yield {
            "phase": "done",
            "write_avg_mb_s": round(sum(write_speeds) / len(write_speeds), 1) if write_speeds else 0,
            "read_avg_mb_s": round(sum(read_speeds) / len(read_speeds), 1) if read_speeds else 0,
            "cache_bypassed": cache_bypassed,
            "iops_write": _iops_from_latencies(write_latencies_ms),
            "iops_read": _iops_from_latencies(read_latencies_ms),
            "avg_latency_write_ms": round(sum(write_latencies_ms) / len(write_latencies_ms), 3) if write_latencies_ms else None,
            "avg_latency_read_ms": round(sum(read_latencies_ms) / len(read_latencies_ms), 3) if read_latencies_ms else None,
        }
    except OSError as exc:
        yield {"phase": "error", "message": str(exc)}
    finally:
        if os.path.exists(test_path):
            try:
                os.remove(test_path)
            except OSError:
                pass


def _iops_from_latencies(latencies_ms: list[float]) -> float | None:
    if not latencies_ms:
        return None
    avg_ms = sum(latencies_ms) / len(latencies_ms)
    return round(1000 / avg_ms, 0) if avg_ms > 0 else None


def _run_unbuffered(
    test_path: str,
    chunk_bytes: int,
    chunks: int,
    chunk_mb: int,
    write_speeds: list[float],
    read_speeds: list[float],
) -> Iterator[dict]:
    if chunk_bytes % _SECTOR_ALIGN != 0:
        # Would fail Win32's alignment requirement anyway -- raise here so
        # the caller falls back to buffered I/O with a clear reason instead
        # of a cryptic ERROR_INVALID_PARAMETER from WriteFile.
        raise OSError(f"chunk size {chunk_bytes} is not a multiple of the {_SECTOR_ALIGN}-byte sector alignment")

    handle = win32file.CreateFile(
        test_path,
        win32file.GENERIC_WRITE,
        0,
        None,
        win32file.CREATE_ALWAYS,
        win32file.FILE_ATTRIBUTE_NORMAL | win32file.FILE_FLAG_NO_BUFFERING | win32file.FILE_FLAG_WRITE_THROUGH,
        None,
    )
    try:
        buf = mmap.mmap(-1, chunk_bytes)
        buf[:] = b"0" * chunk_bytes
        for i in range(chunks):
            start = time.perf_counter()
            win32file.WriteFile(handle, buf)
            elapsed = time.perf_counter() - start
            speed = chunk_mb / elapsed if elapsed > 0 else 0.0
            write_speeds.append(speed)
            yield {"phase": "write", "chunk": i + 1, "of": chunks, "speed_mb_s": round(speed, 1)}
    finally:
        handle.Close()

    handle = win32file.CreateFile(
        test_path,
        win32file.GENERIC_READ,
        0,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_ATTRIBUTE_NORMAL | win32file.FILE_FLAG_NO_BUFFERING,
        None,
    )
    try:
        # Reuses the same mmap buffer across iterations, same as the write
        # loop above -- ReadFile's second return value is a view sized to
        # the actual bytes read, not necessarily still valid as the buffer
        # argument for the *next* call, so it must not overwrite `buf` here.
        buf = mmap.mmap(-1, chunk_bytes)
        for i in range(chunks):
            start = time.perf_counter()
            win32file.ReadFile(handle, buf)
            elapsed = time.perf_counter() - start
            speed = chunk_mb / elapsed if elapsed > 0 else 0.0
            read_speeds.append(speed)
            yield {"phase": "read", "chunk": i + 1, "of": chunks, "speed_mb_s": round(speed, 1)}
    finally:
        handle.Close()


def _run_iops(
    test_path: str,
    total_bytes: int,
    write_latencies_ms: list[float],
    read_latencies_ms: list[float],
) -> Iterator[dict]:
    """Random 4KB write then read, timing each individual operation --
    IOPS/latency matter separately from sequential throughput because seek
    time (HDDs) and command queuing behavior (SSDs/NVMe) show up here in a
    way a single large sequential transfer never reveals."""
    max_offset_blocks = max(total_bytes // _IOPS_BLOCK_SIZE - 1, 1)
    report_every = max(_IOPS_OPS // 8, 1)

    handle = win32file.CreateFile(
        test_path,
        win32file.GENERIC_WRITE,
        0,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_ATTRIBUTE_NORMAL | win32file.FILE_FLAG_NO_BUFFERING | win32file.FILE_FLAG_WRITE_THROUGH,
        None,
    )
    try:
        buf = mmap.mmap(-1, _IOPS_BLOCK_SIZE)
        buf[:] = b"1" * _IOPS_BLOCK_SIZE
        for i in range(_IOPS_OPS):
            offset = random.randint(0, max_offset_blocks) * _IOPS_BLOCK_SIZE
            win32file.SetFilePointer(handle, offset, win32file.FILE_BEGIN)
            start = time.perf_counter()
            win32file.WriteFile(handle, buf)
            write_latencies_ms.append((time.perf_counter() - start) * 1000)
            if (i + 1) % report_every == 0 or i + 1 == _IOPS_OPS:
                yield {"phase": "iops_write", "op": i + 1, "of": _IOPS_OPS}
    finally:
        handle.Close()

    handle = win32file.CreateFile(
        test_path,
        win32file.GENERIC_READ,
        0,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_ATTRIBUTE_NORMAL | win32file.FILE_FLAG_NO_BUFFERING,
        None,
    )
    try:
        buf = mmap.mmap(-1, _IOPS_BLOCK_SIZE)
        for i in range(_IOPS_OPS):
            offset = random.randint(0, max_offset_blocks) * _IOPS_BLOCK_SIZE
            win32file.SetFilePointer(handle, offset, win32file.FILE_BEGIN)
            start = time.perf_counter()
            win32file.ReadFile(handle, buf)
            read_latencies_ms.append((time.perf_counter() - start) * 1000)
            if (i + 1) % report_every == 0 or i + 1 == _IOPS_OPS:
                yield {"phase": "iops_read", "op": i + 1, "of": _IOPS_OPS}
    finally:
        handle.Close()


def _run_buffered(
    test_path: str,
    chunk_bytes: int,
    chunks: int,
    chunk_mb: int,
    write_speeds: list[float],
    read_speeds: list[float],
) -> Iterator[dict]:
    chunk = b"0" * chunk_bytes
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

    with open(test_path, "rb") as f:
        for i in range(chunks):
            start = time.perf_counter()
            data = f.read(chunk_bytes)
            elapsed = time.perf_counter() - start
            if not data:
                break
            speed = chunk_mb / elapsed if elapsed > 0 else 0.0
            read_speeds.append(speed)
            yield {"phase": "read", "chunk": i + 1, "of": chunks, "speed_mb_s": round(speed, 1)}
