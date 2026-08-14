# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
