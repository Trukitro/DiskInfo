# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [6.2.1] - 2026-08-15

### Fixed

- **The 6.2.0 installer couldn't finish installing.** Its post-install
  "Launch DiskInfo" step failed with `CreateProcess failed; code 740
  (The requested operation requires elevation)`, because Inno Setup's
  `[Run]` entries launch via `CreateProcess` by default, which can't
  elevate a process -- and 6.2.0 made `DiskInfo.exe` always require
  elevation. Fixed by adding the `shellexec` flag to that entry, so it
  launches via `ShellExecute` (which can trigger the UAC prompt) instead.
  Desktop/Start Menu shortcuts were never affected by this.

## [6.2.0] - 2026-08-14

### Fixed

- **Benchmark failed with `Permission denied` writing to a drive root**
  (e.g. `C:\diskinfo_benchmark.tmp`) on Windows configurations that
  restrict standard-user writes there. Fixed at the root: DiskInfo now
  always requests admin elevation at launch (`uac_admin=True`, a UAC
  prompt every start) instead of failing on specific drives -- a
  deliberate, user-directed tradeoff. See "Why DiskInfo runs elevated" in
  `DiskInfo-project-plan.md`.
  - Autostart moved from the registry Run key to a Scheduled Task
    (`/rl highest`), since Windows doesn't reliably start an
    elevation-manifested exe from the Run key at logon. The installer's
    old autostart checkbox was removed; autostart is managed from Settings.
- **Settings "Save" silently failed** (`422` from the API, never
  surfaced clearly in the UI): `api-client.js` never set
  `Content-Type: application/json` on PUT requests, so FastAPI parsed the
  body as a raw string instead of an object. Found and fixed during this
  release's own verification pass.

### Added

Continuing `DiskInfo-roadmap.md`'s P0 core, health depth, and a new
Dashboard tying it together:

- Boot disk marking (Drive Info, Dashboard).
- Random 4K IOPS/latency benchmark phase alongside the existing
  sequential throughput test, stored in history alongside it.
- Underperforming-drive detection: flags a benchmark result well below
  what its detected media/bus type should sustain (e.g. an NVMe drive
  benchmarking like SATA), surfaced in the UI and in history.
- Health/temperature history charted over time, with a full raw SMART
  attribute table and a TBW estimate for advanced users (both honestly
  `null`/"--" where the driver doesn't expose them, same as temperature).
- Configurable temperature alert threshold in Settings.
- A new Dashboard landing view: one row per drive with health, free
  space, and performance-vs-expected at a glance, instead of tab-hopping.
- File logging to `%LOCALAPPDATA%\DiskInfo\diskinfo.log` (rotating),
  replacing prints that went nowhere once the app is packaged.
- `ruff` linting and a new CI workflow (`.github/workflows/ci.yml`)
  running lint + the full pytest suite on every push/PR.
- WebSocket integration tests using FastAPI's `TestClient`.

### Investigated, not shipped

- PCIe generation/lane detection and per-disk controller/chipset name:
  tested against this project's own mixed HDD/NVMe hardware --
  `Win32_SCSIControllerDevice` doesn't reliably resolve disk-to-controller
  on this system, and even Windows' inbox controllers report only generic
  names ("Standard NVM Express Controller"), not real chipset info. Not
  worth shipping something that would show "Unknown" for most users.

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
