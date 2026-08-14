"""Partition layout per physical disk, Windows Disk Management style:
physical disk -> ordered segments (partitions and unallocated gaps), each
partition annotated with the logical drive it hosts. Ported from the
original DiskInfov5 desktop app's _load_partition_data()."""

from __future__ import annotations

import psutil
import pythoncom
import win32com.client


def get_partitions() -> list[dict]:
    # Runs inside asyncio.to_thread's executor pool -- COM apartments are
    # per-thread and win32com needs one explicitly initialized before use.
    pythoncom.CoInitialize()
    try:
        return _get_partitions()
    finally:
        pythoncom.CoUninitialize()


def _get_partitions() -> list[dict]:
    locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
    service = locator.ConnectServer(".", "root\\cimv2")

    disks = []
    for disk in service.ExecQuery("SELECT * FROM Win32_DiskDrive"):
        disk_size = int(disk.Size) if disk.Size else 0
        segments = []
        cursor = 0

        for partition in service.ExecQuery(
            f"ASSOCIATORS OF {{Win32_DiskDrive.DeviceID='{disk.DeviceID}'}} "
            "WHERE AssocClass = Win32_DiskDriveToDiskPartition"
        ):
            for logical_disk in service.ExecQuery(
                f"ASSOCIATORS OF {{Win32_DiskPartition.DeviceID='{partition.DeviceID}'}} "
                "WHERE AssocClass = Win32_LogicalDiskToPartition"
            ):
                try:
                    usage = psutil.disk_usage(logical_disk.DeviceID + "\\")
                except (PermissionError, FileNotFoundError, OSError):
                    continue

                start = int(partition.StartingOffset) if getattr(partition, "StartingOffset", None) else cursor
                if start > cursor:
                    segments.append({"unallocated": True, "start": cursor, "size": start - cursor})

                segments.append(
                    {
                        "unallocated": False,
                        "start": start,
                        "size": usage.total,
                        "used": usage.used,
                        "percent_used": round((usage.used / usage.total) * 100, 1) if usage.total else 0,
                        "letter": logical_disk.DeviceID,
                        "filesystem": logical_disk.FileSystem,
                        "type": partition.Type,
                        "bootable": bool(partition.Bootable),
                        "primary": bool(partition.PrimaryPartition),
                    }
                )
                cursor = start + usage.total

        if cursor < disk_size:
            segments.append({"unallocated": True, "start": cursor, "size": disk_size - cursor})

        segments.sort(key=lambda s: s["start"])
        unallocated_total = sum(s["size"] for s in segments if s["unallocated"])

        disks.append(
            {
                "device_id": disk.DeviceID,
                "disk_number": disk.DeviceID.replace("\\\\.\\PHYSICALDRIVE", ""),
                "model": disk.Model,
                "size": disk_size,
                "unallocated": unallocated_total,
                "segments": segments,
            }
        )

    return disks
