# DiskInfo -- project plan / architecture decisions

## Why FastAPI + pywebview instead of customtkinter

`customtkinter` (v1-v5) worked but every UI change meant fighting Tk's
layout system, and the app looked dated next to newer Trukitro tools.
PulseGuard and CuentaClara had already solved this with a small, reusable
pattern: a FastAPI backend serves a static HTML/CSS/JS frontend, and
`pywebview` wraps it in a native, chromeless window (via the system
WebView2 runtime on Windows) so the end result still looks and feels like
a desktop app, not a browser tab. DiskInfo adopts the same pattern rather
than inventing a third one -- see `backend/app/shell.py`.

## Design system

DiskInfo gets its own token set (`frontend/css/tokens.css`), not a copy of
PulseGuard's. Same conventions (CSS custom properties, `Segoe UI Variable`,
the same spacing/radius scale) but its own accent -- a teal
(`#14b8a6` bright / `#0f766e` for text-on-color, chosen so white button
text clears 4.5:1) instead of PulseGuard's blue or CuentaClara's warm
palette. Unlike PulseGuard (dark-only), DiskInfo keeps the light/dark
toggle that was already a named feature in v5, using the same
light-by-default + `data-theme` override approach CuentaClara uses.

## Live updates

A single WebSocket (`/ws`) pushes two kinds of messages:
- `tick`: drive + health snapshots, polled server-side every
  `poll_interval_s` (default 5s, see `backend/app/settings.py`) and
  broadcast to every connected client. Drive Info and Health Status update
  live from this without polling from the frontend.
- `benchmark_progress`: per-chunk read/write speed while a benchmark is
  running, so the Benchmark view can draw a live Chart.js line instead of
  just a final number.

## Notifications and tray

Kept intentionally small for this rewrite: a tray icon (open/exit, closing
the window hides it rather than quitting -- same as PulseGuard) and two
toast notification types via `winotify` -- a drive crossing `low_space_pct`
(default 90%) and a drive's SMART status flipping to predicted failure.
No configurable trigger engine like PulseGuard's; if that's wanted later it
can reuse `backend/app/settings.py` as the place to add it.

## Known limitation: benchmark read speed can be cache-inflated

`benchmark.py` writes then immediately reads back the same temp file using
plain buffered I/O. On a lightly-loaded system, Windows can serve that read
from the page cache instead of the physical drive, so the read number can
come back far higher than the drive can actually sustain (observed: a
mechanical HDD reporting >3000 MB/s read). This bug already existed in
`DiskInfov5.py`'s `benchmark_drive()` -- not introduced by this rewrite.
Write speed is unaffected and is the more trustworthy number for now. A
real fix needs `FILE_FLAG_NO_BUFFERING` (sector-aligned reads/writes via
`win32file`), left for a follow-up since it's real Windows API surface that
needs testing against actual mixed HDD/SSD/NVMe hardware, not something to
land untested in a tool that writes to the user's disks.

## Explicitly out of scope for this rewrite

Carried over from the old `potential_future_features.txt` roadmap, still
not implemented:

- Partition resizing/creation/deletion, file system conversion
- Disk cloning, partition backup/recovery, deleted-file recovery
- Export to CSV/JSON/PDF, automated periodic reports
- Network/NAS drive monitoring, cloud backup integration
- CLI mode, scripting/automation API
- Drive encryption, secure erase
- Multi-language / localization support
- Linux/macOS support (the WMI-based `drives.py`/`health.py`/`partitions.py`
  are Windows-only by design, same as before)
