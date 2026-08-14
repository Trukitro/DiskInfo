"""Drive health via WMI: Win32_DiskDrive.Status plus, where the storage
driver exposes it, real SMART predictive-failure data from
root\\wmi -> MSStorageDriver_FailurePredictStatus. Ported from the original
DiskInfov5 desktop app's get_drive_health()."""

from __future__ import annotations

import pythoncom
import win32com.client


def get_health() -> list[dict]:
    # Runs inside asyncio.to_thread's executor pool -- COM apartments are
    # per-thread and win32com needs one explicitly initialized before use.
    pythoncom.CoInitialize()
    try:
        return _get_health()
    finally:
        pythoncom.CoUninitialize()


def _get_health() -> list[dict]:
    locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
    cimv2 = locator.ConnectServer(".", "root\\cimv2")

    results = []
    for disk in cimv2.ExecQuery("SELECT * FROM Win32_DiskDrive"):
        entry = {
            "device_id": disk.DeviceID,
            "model": disk.Model,
            "status": disk.Status if hasattr(disk, "Status") else "OK",
            "predicted_failure": False,
            "reason": "No issues detected",
            "health_percentage": 100,
        }

        try:
            wmi_ns = locator.ConnectServer(".", "root\\wmi")
            for smart in wmi_ns.ExecQuery("SELECT * FROM MSStorageDriver_FailurePredictStatus"):
                if disk.DeviceID in smart.InstanceName:
                    entry.update(
                        {
                            "predicted_failure": bool(smart.PredictFailure),
                            "reason": smart.Reason if hasattr(smart, "Reason") else "Unknown",
                            "health_percentage": 50 if smart.PredictFailure else 100,
                        }
                    )
        except Exception:
            # Not every storage driver exposes SMART predictive data --
            # disk.Status above already covers the fallback case.
            pass

        results.append(entry)

    return results
