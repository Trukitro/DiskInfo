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
# Total_LBAs_Written -- not universal, but common enough across SSD vendors
# to be worth a best-effort estimate.
_TBW_ATTR_ID = 241
_LBA_SIZE_BYTES = 512


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

        temperature_c, smart_attributes, tbw_estimate_gb = _get_smart_data(locator, disk.DeviceID)
        entry["temperature_c"] = temperature_c
        entry["smart_attributes"] = smart_attributes
        entry["tbw_estimate_gb"] = tbw_estimate_gb
        results.append(entry)

    return results


def _get_smart_data(locator, device_id: str) -> tuple[int | None, list[dict], float | None]:
    """Fetches and parses the raw ATA SMART attribute table once per disk,
    deriving temperature, the full attribute list (for advanced users),
    and a rough TBW estimate from it -- one WMI query instead of three.
    Returns (None, [], None) on any failure; not every storage driver
    exposes MSStorageDriver_ATAPISmartData at all."""
    try:
        wmi_ns = locator.ConnectServer(".", "root\\wmi")
        for smart in wmi_ns.ExecQuery("SELECT * FROM MSStorageDriver_ATAPISmartData"):
            if device_id not in smart.InstanceName:
                continue
            attrs = _parse_smart_attributes(bytes(smart.VendorSpecific))
            return (
                _temperature_from_attrs(attrs),
                [{"id": attr_id, **values} for attr_id, values in sorted(attrs.items())],
                _tbw_from_attrs(attrs),
            )
    except Exception:
        pass
    return None, [], None


def _parse_smart_attributes(raw: bytes) -> dict[int, dict[str, int]]:
    """raw is the 512-byte VendorSpecific SMART data blob: a 2-byte
    structure revision followed by up to 30 fixed-size 12-byte attribute
    records (id, flags[2], current, worst, raw_value[6], reserved). The
    6-byte raw value is read as a little-endian integer -- big enough for
    fields like TBW's LBA count, not just a single byte like temperature
    needs."""
    attrs: dict[int, dict[str, int]] = {}
    for i in range(30):
        offset = 2 + i * 12
        if offset + 12 > len(raw):
            break
        attr_id = raw[offset]
        if attr_id == 0:
            continue
        attrs[attr_id] = {
            "current": raw[offset + 3],
            "worst": raw[offset + 4],
            "raw": int.from_bytes(raw[offset + 5 : offset + 11], "little"),
        }
    return attrs


def _temperature_from_attrs(attrs: dict[int, dict[str, int]]) -> int | None:
    for attr_id in _TEMPERATURE_ATTR_IDS:
        entry = attrs.get(attr_id)
        if entry is None:
            continue
        low_byte = entry["raw"] & 0xFF
        # Sanity bound: 0 or an absurdly high byte value is more likely a
        # parsing artifact on this vendor's layout than a real reading.
        if 0 < low_byte < 128:
            return low_byte
    return None


def _tbw_from_attrs(attrs: dict[int, dict[str, int]]) -> float | None:
    """Rough estimate, not a spec-guaranteed value -- attribute 241's raw
    value is conventionally a count of 512-byte LBAs written, but the unit
    isn't standardized across vendors the same way temperature's isn't."""
    entry = attrs.get(_TBW_ATTR_ID)
    if entry is None or entry["raw"] <= 0:
        return None
    return round(entry["raw"] * _LBA_SIZE_BYTES / (1024**3), 1)


def _parse_smart_temperature(raw: bytes) -> int | None:
    """Kept as a small direct entry point (used by tests and previously by
    callers) on top of the shared attribute parser."""
    return _temperature_from_attrs(_parse_smart_attributes(raw))
