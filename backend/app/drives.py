"""Physical drive enumeration: WMI Win32_DiskDrive joined to logical drive
letters via the DiskDrive -> DiskPartition -> LogicalDisk associator chain,
sized with psutil.disk_usage. Ported from the original DiskInfov5 desktop
app's get_drive_mappings()."""

from __future__ import annotations

import os
import re

import psutil
import pythoncom
import win32com.client

# MSFT_PhysicalDisk.BusType -- see the Storage Management API docs. Index 0
# ("Unknown") deliberately omitted from lookups below so an unrecognized
# code falls through to "Unknown" the same way a missing key would.
_BUS_TYPES = {
    1: "SCSI",
    2: "ATAPI",
    3: "ATA",
    4: "IEEE 1394",
    5: "SSA",
    6: "Fibre Channel",
    7: "USB",
    8: "RAID",
    9: "iSCSI",
    10: "SAS",
    11: "SATA",
    12: "SD",
    13: "MMC",
    15: "File Backed Virtual",
    16: "Storage Spaces",
    17: "NVMe",
    18: "Microsoft Reserved",
}

# MSFT_PhysicalDisk.MediaType -- 0 (Unspecified) omitted so it's treated the
# same as "not reported", triggering the string-guess fallback below.
_MEDIA_TYPES = {3: "HDD", 4: "SSD", 5: "SCM"}

_PHYSICAL_DRIVE_RE = re.compile(r"PHYSICALDRIVE(\d+)", re.IGNORECASE)


def _wmi_service(namespace: str = "root\\cimv2"):
    locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
    return locator.ConnectServer(".", namespace)


def _physical_drive_index(device_id: str) -> str | None:
    match = _PHYSICAL_DRIVE_RE.search(device_id)
    return match.group(1) if match else None


def _get_physical_disk_info() -> dict[str, dict]:
    """Maps physical drive index ("0", "1", ...) -> {media_type, bus_type},
    read from MSFT_PhysicalDisk (WMI namespace root\\Microsoft\\Windows\\Storage)
    -- the modern Storage Management API, same source Windows Settings and
    PowerShell's Get-PhysicalDisk use. Only available on Windows
    8/Server 2012 and later; returns {} on any failure (missing namespace,
    missing class, permission issue) so callers fall back cleanly to the
    older string-guessing method instead of erroring out."""
    try:
        service = _wmi_service("root\\Microsoft\\Windows\\Storage")
        info: dict[str, dict] = {}
        for disk in service.ExecQuery("SELECT DeviceId, MediaType, BusType FROM MSFT_PhysicalDisk"):
            media_type = _MEDIA_TYPES.get(disk.MediaType)
            bus_type = _BUS_TYPES.get(disk.BusType, "Unknown")
            if media_type == "SSD" and bus_type == "NVMe":
                media_type = "NVMe SSD"
            elif media_type == "SSD" and bus_type in ("SATA", "ATA"):
                media_type = "SATA SSD"
            info[disk.DeviceId] = {"media_type": media_type, "bus_type": bus_type}
        return info
    except Exception:
        return {}


def _infer_media_type(model: str | None, media_type: str | None) -> str:
    """Fallback for when MSFT_PhysicalDisk isn't available: guesses from the
    model name string, which only works when the vendor happens to put
    "SSD"/"NVMe"/etc. in the model. Kept for older Windows versions and as
    a safety net, not the primary path anymore."""
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
    physical_disk_info = _get_physical_disk_info()
    # os.environ["SystemDrive"] is always set by Windows (e.g. "C:") and is
    # the cheapest reliable way to identify the boot volume -- no extra WMI
    # query needed.
    system_drive = (os.environ.get("SystemDrive") or "C:").rstrip("\\").upper() + "\\"
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

        index = _physical_drive_index(disk.DeviceID)
        info = physical_disk_info.get(index) if index else None
        if info and info["media_type"]:
            media_type = info["media_type"]
            bus_type = info["bus_type"]
        else:
            media_type = _infer_media_type(disk.Model, getattr(disk, "MediaType", None))
            bus_type = disk.InterfaceType or "Unknown"

        is_boot = any(p["mountpoint"].upper() == system_drive for p in partitions)

        drives.append(
            {
                "device_id": disk.DeviceID,
                "model": disk.Model or disk.DeviceID,
                "interface": disk.InterfaceType or "Unknown",
                "media_type": media_type,
                "bus_type": bus_type,
                "size": int(disk.Size) if disk.Size else 0,
                "is_boot": is_boot,
                "partitions": partitions,
            }
        )

    return drives
