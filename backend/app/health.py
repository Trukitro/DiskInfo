"""Drive health via WMI: Win32_DiskDrive.Status plus, where the storage
driver exposes it, real SMART predictive-failure data from
root\\wmi -> MSStorageDriver_FailurePredictStatus. Ported from the original
DiskInfov5 desktop app's get_drive_health()."""

from __future__ import annotations

import pythoncom
import win32com.client

# ATA SMART attribute IDs conventionally used for temperature -- checked in
# this order since 194 is by far the more common/reliable of the two.
_TEMPERATURE_ATTR_IDS = (194, 190)


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

        entry["temperature_c"] = _get_smart_temperature(locator, disk.DeviceID)
        results.append(entry)

    return results


def _get_smart_temperature(locator, device_id: str) -> int | None:
    """Best-effort SMART temperature (attribute 194, falling back to 190),
    parsed from the raw ATA SMART attribute table exposed via
    MSStorageDriver_ATAPISmartData.VendorSpecific. This format is not
    standardized across vendors -- returns None on any unexpected shape
    rather than guessing, since a wrong temperature reading is worse than
    an honest "not available."""
    try:
        wmi_ns = locator.ConnectServer(".", "root\\wmi")
        for smart in wmi_ns.ExecQuery("SELECT * FROM MSStorageDriver_ATAPISmartData"):
            if device_id not in smart.InstanceName:
                continue
            return _parse_smart_temperature(bytes(smart.VendorSpecific))
    except Exception:
        pass
    return None


def _parse_smart_temperature(raw: bytes) -> int | None:
    """raw is the 512-byte VendorSpecific SMART data blob: a 2-byte
    structure revision followed by up to 30 fixed-size 12-byte attribute
    records (id, flags[2], current, worst, raw_value[6], reserved)."""
    attrs: dict[int, int] = {}
    for i in range(30):
        offset = 2 + i * 12
        if offset + 12 > len(raw):
            break
        attr_id = raw[offset]
        if attr_id == 0:
            continue
        attrs[attr_id] = raw[offset + 5]  # first byte of the 6-byte raw value

    for attr_id in _TEMPERATURE_ATTR_IDS:
        value = attrs.get(attr_id)
        # Sanity bound: 0 or an absurdly high byte value is more likely a
        # parsing artifact on this vendor's layout than a real reading.
        if value is not None and 0 < value < 128:
            return value
    return None
