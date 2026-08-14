# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [6.1.0] - 2026-08-14

Robustness pass: fixes the two known-wrong things from 6.0.0, plus 9 more
items pulled from `DiskInfo-roadmap.md`.

### Fixed

- **Benchmark read speed was cache-inflated.** The write phase used
  buffered I/O, so the read phase right after could be served from
  Windows' page cache instead of the physical drive -- a mechanical HDD
  could report >3000 MB/s "read." Now uses `FILE_FLAG_NO_BUFFERING` with
  sector-aligned I/O (via `mmap`) so both phases hit the physical media;
  falls back to the old buffered path (flagged `cache_bypassed: false` in
  the UI) if an unusual filesystem rejects the flag. Verified on this
  project's own HDD: the same drive that used to report >3000 MB/s now
  reports ~100 MB/s, matching a 7200RPM drive's real throughput.
- **Drive type detection was a model-name guess.** Replaced with
  `MSFT_PhysicalDisk` (the same Storage Management API Windows Settings
  and `Get-PhysicalDisk` use), which exposes real `MediaType`/`BusType`
  instead of hoping the vendor put "SSD" in the model string. One drive on
  this project's own test hardware was previously misclassified as
  "Fixed hard disk media" and now correctly shows "NVMe SSD."

### Added

- Settings page, backed by a single centralized `settings.json` (poll
  interval, low-space threshold, notifications, autostart, port).
- Autostart toggle in Settings, writing directly to the same registry key
  the installer's checkbox uses -- no reinstall needed to change it.
- Configurable benchmark size (Quick/Standard/Thorough presets) instead of
  a fixed 200MB.
- Benchmark history: past runs are stored locally (SQLite) and shown in a
  trend table under the chart.
- Live per-drive read/write throughput, shown as a sparkline on each Drive
  Info card; also used to warn before starting a benchmark if the target
  drive already has significant I/O in flight.
- Experimental SMART temperature reading (attribute 194/190) on Health
  Status, where the driver exposes it -- shows "--" rather than a guess
  when it doesn't.
- CSV/JSON export for the Drive Info, Health Status, and Partitions views.
- `backend/tests/`: first pytest suite for this project (drive/media-type
  logic, SMART parsing, settings/history persistence, and the benchmark's
  buffered-fallback path).

## [6.0.0] - 2026-08-14

### Changed

- **Complete rewrite of the desktop app**, moving off `customtkinter` onto
  the same web-native stack as [PulseGuard](https://github.com/Trukitro/PulseGuard)
  and [CuentaClara](https://github.com/Trukitro/CuentaClara): a FastAPI
  backend served inside a chromeless `pywebview` window, with a vanilla
  HTML/CSS/JS frontend (Fluent UI web components, Chart.js) instead of a
  native Tk widget tree.
- Drive Info, Health Status, Partitions, and Benchmark all kept their
  original functionality, ported from `DiskInfov5.py`'s WMI/psutil logic
  into `backend/app/{drives,health,partitions,benchmark}.py`.
- The disk benchmark now streams live per-chunk speed over a WebSocket
  (rendered as a live Chart.js line) instead of running a single 10MB
  transfer and only showing a final number.
- The light/dark appearance toggle from v5 is preserved (now backed by CSS
  custom properties instead of `customtkinter`'s appearance modes), plus a
  new "System" option that follows the OS theme.
- Added a system tray icon (minimize instead of quit on close) and native
  Windows toast notifications for drives nearing full and predicted SMART
  failures.
- Packaging moved from a bare PyInstaller `.exe` to a proper Windows
  installer (Inno Setup), built and attached to GitHub Releases
  automatically on tag push.

### Removed

- `DiskInfov5.py` and the unfinished `DiskInfo v6/` customtkinter draft.

## [5.0.0] and earlier

See the old `customtkinter` app's in-app About page for the pre-rewrite
history (partition management view, SMART health monitoring, benchmarking,
dark mode) -- not reproduced here since none of it shipped as tagged
releases.
