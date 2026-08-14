<p align="center">
  <img src="assets/logo.png" alt="DiskInfo logo" width="140">
</p>

<h1 align="center">DiskInfo</h1>

DiskInfo is a comprehensive disk management and monitoring tool that provides detailed information about your storage devices. It helps you monitor disk health, performance, and usage, and includes features like live benchmarking and partition management.

A FastAPI backend running inside a native (chromeless) desktop window, with a web frontend -- same architecture as [PulseGuard](https://github.com/Trukitro/PulseGuard) and [CuentaClara](https://github.com/Trukitro/CuentaClara).

---

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Changelog](#changelog)
- [Creator](#creator)
- [License](#license)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Acknowledgments](#acknowledgments)

---

## Features

- **Drive Info**: Real HDD/SSD/NVMe classification and bus type (via the same Storage Management API Windows Settings uses, not a guess from the model name), capacity/usage, and a live per-drive read/write activity sparkline.
- **Health Status**: SMART predictive-failure data where the driver exposes it, plus experimental SMART temperature.
- **Partitions**: Detailed partition information in a Windows Disk Management-style interface.
- **Benchmark**: Read/write speed test that bypasses the Windows page cache (`FILE_FLAG_NO_BUFFERING`) so results reflect the physical drive, not RAM -- configurable size (Quick/Standard/Thorough), a live chart, and local run history.
- **Settings**: Poll interval, low-space threshold, notifications, and autostart, all editable in-app.
- **Export**: CSV/JSON export of Drive Info, Health Status, and Partitions data.
- **Light / Dark / System theme**: Switch appearance, or follow the OS.
- **Tray icon + notifications**: Minimizes to the tray instead of quitting; native Windows toasts for low disk space or a predicted drive failure.

---

## Installation

### Option A -- installer (recommended)
1. Go to the [Releases](https://github.com/Trukitro/DiskInfo/releases) page.
2. Download and run the latest `DiskInfoSetup.exe`.
3. If Windows SmartScreen warns you (the installer isn't code-signed), click **More info** → **Run anyway**.

### Option B -- run from source

**Prerequisites**
- Python 3.10+
- Windows (the drive/health/partition modules use WMI and are Windows-only)

**Steps**
```bash
git clone https://github.com/Trukitro/DiskInfo.git
cd DiskInfo
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt
python backend/run.py
```

**Build a standalone .exe**
```bash
cd backend
pip install pyinstaller
pyinstaller diskinfo.spec --noconfirm
```
The app will be in `backend/dist/DiskInfo/`.

---

## Usage

Launch the app (installed shortcut, or `python backend/run.py`) and use the sidebar to switch between Drive Info, Health Status, Partitions, and Benchmark. Closing the window minimizes DiskInfo to the tray; use the tray icon's **Exit** to actually quit.

### Dev mode (frontend only, no pywebview window)
```bash
python -m uvicorn app.main:app --reload --app-dir backend --port 8745
```
Then open `http://127.0.0.1:8745/` in any browser. Useful for iterating on the frontend without rebuilding the native window each time.

---

## Screenshots

The screenshots from the old `customtkinter` app were removed since they no longer
match the rewritten UI. Run the app (see [Usage](#usage)) to see the current
Drive Info / Health Status / Partitions / Benchmark views -- fresh screenshots
are on the list to add back here.

---

## Architecture

```
backend/    FastAPI app + pywebview shell (drives/health/partitions/benchmark logic, tray, notifications)
frontend/   Static HTML/CSS/JS UI served by the backend (Fluent UI web components, Chart.js)
installer/  Inno Setup script
assets/     App icon (icon.ico) and README logo (logo.png)
```

See [DiskInfo-project-plan.md](DiskInfo-project-plan.md) for the reasoning behind these choices and what's deliberately out of scope.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## Creator

Created by EtchTechnologies ([Rikion](https://github.com/Trukitro)).

---

## Troubleshooting

1. **Missing dependencies when running from source**: `pip install -r backend/requirements.txt`.
2. **Windows SmartScreen warning**: click **More info** → **Run anyway**. The installer isn't code-signed but is safe if downloaded from the official [Releases](https://github.com/Trukitro/DiskInfo/releases) page.
3. **Permission errors accessing a drive**: some drives (e.g. system-protected volumes) may need the app run as administrator.
4. **No SMART data for a drive**: not every drive/driver exposes `MSStorageDriver_FailurePredictStatus`; DiskInfo falls back to the drive's basic WMI status in that case.
5. **Benchmark fails**: make sure the selected drive is writable and has at least 200MB free.

If you hit something else, open an issue on the [GitHub repository](https://github.com/Trukitro/DiskInfo/issues).

---

## Roadmap

See the "Explicitly out of scope" section of [DiskInfo-project-plan.md](DiskInfo-project-plan.md) for the full list (partition resizing, disk cloning, export/reporting, network drives, CLI, encryption, localization, cross-platform support).

---

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) and [pywebview](https://pywebview.flowrl.com/) for the app shell.
- [Fluent UI Web Components](https://github.com/microsoft/fluentui) and [Chart.js](https://www.chartjs.org/) for the frontend.
- [psutil](https://github.com/giampaolo/psutil) and [pywin32](https://github.com/mhammond/pywin32) for system and disk information.
- The Python community for their support and contributions.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
