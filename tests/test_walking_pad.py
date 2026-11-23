"""Tests for the WalkingPad Bluetooth client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.king_smith import walking_pad as wp

from .helpers import raw


async def test_api_roundtrip():
    client = MagicMock(is_connected=True)
    nchar = MagicMock(uuid=wp.CHAR_NOTIFY, handle=11, properties=["notify"])
    wchar = MagicMock(
        uuid=wp.CHAR_WRITE, handle=14, properties=["write", "write-without-response"]
    )
    client.services = [MagicMock(uuid="fe00", characteristics=[nchar, wchar])]
    dropped = []  # the "pad" ignores the first status request
    notify = {}

    async def start_notify(char, cb):
        notify["cb"] = cb

    client.start_notify = start_notify
    writes = []

    async def write(char, data, response=None):
        assert response is False
        writes.append((char, bytes(data)))
        if data[1:3] == bytes([0xA2, 0]):
            if not dropped:
                dropped.append(data)
                return
            asyncio.get_running_loop().call_soon(
                notify["cb"], None, bytearray(raw(speed=25, t=10, steps=7, belt=1))
            )

    client.write_gatt_char = write
    client.disconnect = AsyncMock()
    pushed, dis = [], []
    with (
        patch.object(wp, "establish_connection", AsyncMock(return_value=client)) as est,
        patch.object(wp, "MIN_COMMAND_SPACING", 0.01),
        patch.object(wp, "SETTLE_DELAY", 0),
        patch.object(wp, "STATUS_TIMEOUT", 0.05),
    ):
        api = wp.WalkingPadApi(
            MagicMock(address="AA", name="WalkingPad"),
            pushed.append,
            lambda: dis.append(1),
        )
        await api.connect()
        s = await api.request_status()
        assert s.speed == 2.5 and s.steps == 7 and pushed == []
        notify["cb"](None, bytearray(raw(speed=30)))  # unsolicited -> push callback
        assert pushed[0].speed == 3.0
        await api.start()
        assert len(writes) == 4  # status retried once
        assert [w[1].hex() for w in writes[2:]] == ["f7a20201a5fd", "f7a20401a7fd"]
        assert all(w[0] is wchar for w in writes)
        cb = est.call_args.kwargs["disconnected_callback"]
        cb(client)
        assert dis == [1] and not api.connected
