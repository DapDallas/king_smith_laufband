"""Helpers for the WalkingPad tests."""

MAC = "AA:BB:CC:DD:EE:FF"


def raw(speed=0, mode=1, t=0, dist=0, steps=0, belt=0) -> bytes:
    """Build a status notification (speed in 0.1 km/h, dist in 10 m)."""
    return bytes(
        [
            0xF8,
            0xA2,
            belt,
            speed,
            mode,
            *t.to_bytes(3, "big"),
            *dist.to_bytes(3, "big"),
            *steps.to_bytes(3, "big"),
            0,
            0,
            0,
            0xFD,
        ]
    )
