"""Rough expected sequential write-speed floors per drive category, used
to flag a benchmark result well below what its detected type should
sustain -- e.g. an NVMe drive benchmarking like a SATA SSD usually means
AHCI/compatibility mode, a bad slot, or a throttled/degraded drive, not
just "a slow NVMe drive." Deliberately approximate floors, not precise
specs -- the goal is catching drives running far outside their category,
not grading exact performance."""

from __future__ import annotations

# bus_type -> minimum expected sequential write MB/s, for SSD-family
# drives only (HDDs are handled by media_type below since bus_type alone
# doesn't distinguish a SATA HDD from a SATA SSD).
_BUS_TYPE_SSD_FLOORS = {
    "NVMe": 800.0,
    "SATA": 350.0,
}
_GENERIC_SSD_FLOOR = 300.0
_HDD_FLOOR = 40.0


def expected_floor_mb_s(media_type: str, bus_type: str) -> float | None:
    media_lower = (media_type or "").lower()
    if "hdd" in media_lower:
        return _HDD_FLOOR
    if "ssd" in media_lower or "scm" in media_lower:
        return _BUS_TYPE_SSD_FLOORS.get(bus_type, _GENERIC_SSD_FLOOR)
    return None  # unrecognized media type -- don't guess a floor


def evaluate(media_type: str, bus_type: str, write_avg_mb_s: float) -> tuple[bool, str | None]:
    """Returns (underperforming, reason). reason is None whenever
    underperforming is False, including the "couldn't evaluate" case."""
    floor = expected_floor_mb_s(media_type, bus_type)
    if floor is None or write_avg_mb_s <= 0:
        return False, None
    if write_avg_mb_s < floor:
        reason = (
            f"{media_type} over {bus_type} wrote at {write_avg_mb_s:.0f} MB/s, "
            f"below the ~{floor:.0f} MB/s expected for this category -- "
            "check for AHCI/compatibility mode, a bad slot/cable, or drive health."
        )
        return True, reason
    return False, None
