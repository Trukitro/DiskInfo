"""Physical drive enumeration: WMI Win32_DiskDrive joined to logical drive
letters via the DiskDrive -> DiskPartition -> LogicalDisk associator chain,
sized with psutil.disk_usage. Ported from the original DiskInfov5 desktop
app's get_drive_mappings()."""

from __future__ import annotations

import psutil
import pythoncom
import win32com.client


def _wmi_service(namespace: str = "root\\cimv2"):
    locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
    return locator.ConnectServer(".", namespace)


def _infer_media_type(model: str | None, media_type: str | None) -> str:
    model_lower = (model or "").lower()
    if "nvme" in model_lower:
        return "NVMe SSD"
    if "m.2" in model_lower:
        return "M.2 SSD"
    if "ssd" in model_lower:
        return "SSD"
    if "hdd" in model_lower or "hard drive" in model_lower:
        return "HDD"
    if "scsi" in model_lower:
        return "SCSI Drive"
    return media_type or "Unknown"


def get_drives() -> list[dict]:
    """One entry per physical disk, each with its mounted partitions."""
    # Runs inside asyncio.to_thread's executor pool -- COM apartments are
    # per-thread and win32com needs one explicitly initialized before use.
    pythoncom.CoInitialize()
    try:
        return _get_drives()
    finally:
        pythoncom.CoUninitialize()


def _get_drives() -> list[dict]:
    service = _wmi_service()
    drives = []

    for disk in service.ExecQuery("SELECT * FROM Win32_DiskDrive"):
        partitions = []
        for partition in service.ExecQuery(
            f"ASSOCIATORS OF {{Win32_DiskDrive.DeviceID='{disk.DeviceID}'}} "
            "WHERE AssocClass = Win32_DiskDriveToDiskPartition"
        ):
            for logical_disk in service.ExecQuery(
                f"ASSOCIATORS OF {{Win32_DiskPartition.DeviceID='{partition.DeviceID}'}} "
                "WHERE AssocClass = Win32_LogicalDiskToPartition"
            ):
                mountpoint = logical_disk.DeviceID + "\\"
                try:
                    usage = psutil.disk_usage(mountpoint)
                except (PermissionError, FileNotFoundError, OSError):
                    continue
                partitions.append(
                    {
                        "mountpoint": mountpoint,
                        "used": usage.used,
                        "total": usage.total,
                        "percent": usage.percent,
                    }
                )

        drives.append(
            {
                "device_id": disk.DeviceID,
                "model": disk.Model or disk.DeviceID,
                "interface": disk.InterfaceType or "Unknown",
                "media_type": _infer_media_type(disk.Model, getattr(disk, "MediaType", None)),
                "size": int(disk.Size) if disk.Size else 0,
                "partitions": partitions,
            }
        )

    return drives
