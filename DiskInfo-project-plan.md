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

## Fixed in 6.1.0: benchmark read speed was cache-inflated

`benchmark.py` used to write then immediately read back the same temp file
with plain buffered I/O, so Windows could serve the read from the page
cache instead of the physical drive (observed: a mechanical HDD reporting
>3000 MB/s read). Fixed by opening the file with `FILE_FLAG_NO_BUFFERING`
(sector-aligned via `mmap.mmap(-1, size)`, which is page/sector-aligned on
Windows for free) so both phases hit the physical media. Verified against
this project's own mixed HDD/NVMe hardware: the same drive that used to
report an impossible >3000 MB/s now reports ~100 MB/s, in line with a
7200RPM HDD's real sustained throughput.

Falls back to the old buffered path (with `cache_bypassed: false` on the
`done` event, surfaced in the UI) if `FILE_FLAG_NO_BUFFERING` is rejected
by an unusual filesystem or virtual disk -- an honest caveat instead of a
hard failure.

## Why DiskInfo runs elevated (as of 6.2.0)

A real bug forced this decision: running the benchmark against `C:` failed
with `Permission denied` writing `diskinfo_benchmark.tmp` to the drive
root, because that specific Windows configuration doesn't allow standard
users to write there. Rather than patch around that one case, the app now
always requests admin elevation at launch (`uac_admin=True` in
`backend/diskinfo.spec`, which embeds a `requireAdministrator` manifest) --
a UAC prompt on every start, traded for never hitting a silent permission
failure on any drive root, and because section 4 of the roadmap (TRIM,
power modes) will need admin too. This was an explicit user decision,
overriding the roadmap's earlier "detect and elevate only when needed"
idea in section 8 in favor of one predictable model decided once.

**Consequence for autostart**: Windows does not reliably start an
elevation-manifested exe from the `HKCU\...\Run` registry key at logon --
it either silently fails or never prompts. `backend/app/autostart.py`
was rewritten to use a Scheduled Task (`schtasks /sc onlogon /rl highest`)
instead, which Windows does start elevated without a prompt. The
installer's old autostart checkbox (which wrote to the Run key) was
removed for the same reason -- autostart is managed solely from the
in-app Settings page now, since it has to run *after* the app is already
elevated to create the scheduled task.

## Explicitly out of scope for this rewrite

Carried over from the old `potential_future_features.txt` roadmap, still
not implemented:

- Partition resizing/creation/deletion, file system conversion
- Disk cloning, partition backup/recovery, deleted-file recovery
- **Reporting**: PDF-formatted reports, automated/scheduled report
  generation, delivery to an external server. A plain CSV/JSON export of
  data already shown on screen is *not* covered by this exclusion -- see
  below.
- Network/NAS drive monitoring, cloud backup integration
- CLI mode, scripting/automation API
- Drive encryption, secure erase
- Multi-language / localization support
- Linux/macOS support (the WMI-based `drives.py`/`health.py`/`partitions.py`
  are Windows-only by design, same as before)

### Scope clarification: export vs. reporting

The original "Export to CSV/JSON/PDF, automated periodic reports" exclusion
bundled two different things together. Resolved as of the roadmap review
after v6.0.0:

- **In scope**: a plain CSV/JSON export button for data already rendered in
  a view (drives, health, partitions) -- no formatting engine, no schedule,
  no delivery mechanism, just "write out what's on screen."
- **In scope**: a diagnostic snapshot for support requests (specs + SMART +
  space + config bundled into one file to attach to a GitHub issue) -- this
  is a troubleshooting tool, not a reporting feature, even though it also
  produces a file.
- **Still out of scope**: PDF/formatted reports, anything scheduled or
  automated, anything sent somewhere on the user's behalf.
