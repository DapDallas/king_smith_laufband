"""Tests for the King Smith WalkingPad integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.king_smith.const import (
    DOMAIN,
    EVENT_SESSION_DONE,
    EVENT_SESSION_START,
)
from custom_components.king_smith.walking_pad import WalkingPadStatus, _command

from .helpers import MAC, raw


async def test_protocol():
    assert _command(0xA2, 0, 0) == bytes([247, 162, 0, 0, 162, 253])
    assert _command(0xA2, 1, 30) == bytes([247, 162, 1, 30, (162 + 1 + 30) % 256, 253])
    s = WalkingPadStatus.from_bytes(raw(speed=35, t=125, dist=123, steps=200, belt=1))
    assert (s.speed, s.time, s.distance, s.steps, s.belt_state) == (
        3.5,
        125,
        1.23,
        200,
        1,
    )
    assert WalkingPadStatus.from_bytes(b"\xf8\xa7" + bytes(18)) is None


@pytest.fixture
def pad():
    statuses = []
    api = MagicMock()
    api.connected = True
    api.connect = AsyncMock()
    api.disconnect = AsyncMock()
    api.start = AsyncMock()
    api.stop = AsyncMock()
    api.set_speed = AsyncMock()

    async def request():
        return WalkingPadStatus.from_bytes(
            statuses.pop(0) if len(statuses) > 1 else statuses[0]
        )

    api.request_status = AsyncMock(side_effect=request)
    with (
        patch(
            "custom_components.king_smith.coordinator.WalkingPadApi", return_value=api
        ),
        patch(
            "custom_components.king_smith.bluetooth.async_ble_device_from_address",
            return_value=MagicMock(address=MAC),
        ),
        patch(
            "custom_components.king_smith.coordinator.bluetooth.async_ble_device_from_address",
            return_value=MagicMock(address=MAC),
        ),
        patch(
            "custom_components.king_smith.bluetooth.async_register_callback",
            return_value=lambda: None,
        ),
        patch("custom_components.king_smith.bluetooth.async_rediscover_address"),
    ):
        yield api, statuses


async def setup(hass):
    hass.config.components.add("bluetooth")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_NAME: "Pad", CONF_MAC: MAC},
        unique_id=MAC.lower(),
        title="Pad",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def refresh(hass, entry):
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_entities_and_session(hass: HomeAssistant, pad):
    api, statuses = pad
    statuses.append(raw(mode=2))
    entry = await setup(hass)
    ents = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    ids = sorted(e.unique_id for e in ents)
    assert ids == sorted(
        f"{MAC}_{k}"
        for k in [
            "speed",
            "speed",
            "distance",
            "time",
            "steps",
            "step_cadence",
            "total_distance",
            "total_time",
            "total_steps",
            "switch",
        ]
    )
    assert hass.states.get("switch.pad").state == "off"
    assert hass.states.get("sensor.pad_total_steps").state == "0"

    starts = async_capture_events(hass, EVENT_SESSION_START)
    dones = async_capture_events(hass, EVENT_SESSION_DONE)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.pad"}, blocking=True
    )
    api.start.assert_awaited_once()
    assert hass.states.get("switch.pad").state == "on"

    statuses[:] = [
        raw(speed=30, t=60, dist=5, steps=100, belt=1),
        raw(speed=30, t=120, dist=10, steps=210, belt=1),
        raw(speed=0, t=0, mode=2),
    ]
    await refresh(hass, entry)
    assert len(starts) == 1
    await refresh(hass, entry)
    assert hass.states.get("sensor.pad_steps").state == "210"
    assert float(hass.states.get("sensor.pad_step_cadence").state) == 110.0
    assert hass.states.get("sensor.pad_total_steps").state == "210"
    assert hass.states.get("sensor.pad_total_distance").state == "0.1"
    await refresh(hass, entry)
    assert len(dones) == 1
    dev = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, MAC)})
    assert dones[0].data["device_id"] == dev.id and dones[0].data["steps"] == 210
    assert hass.states.get("sensor.pad_total_steps").state == "210"

    # new session adds up
    statuses[:] = [raw(speed=20, t=30, steps=50, belt=1)]
    await refresh(hass, entry)
    assert hass.states.get("sensor.pad_total_steps").state == "260"

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.pad_speed", "value": 4.5},
        blocking=True,
    )
    api.set_speed.assert_awaited_with(4.5)
    assert hass.states.get("number.pad_speed").state == "4.5"

    assert await hass.config_entries.async_unload(entry.entry_id)
    api.disconnect.assert_awaited()


async def test_device_trigger(hass: HomeAssistant, pad):
    api, statuses = pad
    statuses.append(raw(mode=2))
    entry = await setup(hass)
    dev = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, MAC)})
    from homeassistant.components.device_automation import (
        DeviceAutomationType,
        async_get_device_automations,
    )

    triggers = await async_get_device_automations(
        hass, DeviceAutomationType.TRIGGER, [dev.id]
    )
    assert sorted(t["type"] for t in triggers[dev.id] if t["domain"] == DOMAIN) == [
        "session_done",
        "session_start",
    ]
    calls = async_capture_events(hass, "test_fired")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": dev.id,
                        "type": t,
                    },
                    "action": {"event": "test_fired", "event_data": {"t": t}},
                }
                for t in ("session_start", "session_done")
            ]
        },
    )
    statuses[:] = [raw(speed=30, t=60, steps=10, belt=1), raw(mode=2)]
    await refresh(hass, entry)
    await refresh(hass, entry)
    assert [c.data["t"] for c in calls] == ["session_start", "session_done"]


async def test_unavailable_when_off(hass: HomeAssistant, pad):
    api, statuses = pad
    statuses.append(raw(mode=2))
    entry = await setup(hass)
    from custom_components.king_smith.walking_pad import WalkingPadError

    api.request_status.side_effect = WalkingPadError("gone")
    await refresh(hass, entry)
    assert hass.states.get("switch.pad").state == "unavailable"


async def test_config_flow(hass: HomeAssistant):
    hass.config.components.add("bluetooth")
    with (
        patch(
            "custom_components.king_smith.config_flow.bluetooth.async_discovered_service_info",
            return_value=[],
        ),
        patch("custom_components.king_smith.async_setup_entry", return_value=True),
    ):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert r["step_id"] == "user"
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {CONF_NAME: "Pad", CONF_MAC: "nope"}
        )
        assert r["errors"] == {CONF_MAC: "invalid_mac"}
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {CONF_NAME: "Pad", CONF_MAC: "aa:bb:cc:dd:ee:ff"}
        )
        assert r["type"] == "create_entry" and r["data"][CONF_MAC] == MAC
        e = hass.config_entries.async_entries(DOMAIN)[0]
        assert e.unique_id == "aa:bb:cc:dd:ee:ff"
        r = await hass.config_entries.options.async_init(e.entry_id)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"scan_interval": 3}
        )
        assert r["type"] == "create_entry" and e.options == {"scan_interval": 3}


async def test_start_countdown_autostop(hass: HomeAssistant, pad):
    from datetime import timedelta

    api, statuses = pad
    statuses.append(raw(mode=2))
    entry = await setup(hass)
    coord = entry.runtime_data
    assert coord.update_interval == timedelta(seconds=5)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.pad"}, blocking=True
    )
    assert hass.states.get("switch.pad").state == "on"
    assert coord.update_interval == timedelta(seconds=1)

    # countdown: pad in manual mode, belt not moving yet -> switch stays on
    statuses[:] = [raw(mode=1, speed=0)]
    await refresh(hass, entry)
    assert hass.states.get("switch.pad").state == "on"
    assert coord.update_interval == timedelta(seconds=1)

    # belt runs: real speed shown immediately
    statuses[:] = [raw(mode=1, speed=20, t=1, belt=1)]
    await refresh(hass, entry)
    assert hass.states.get("sensor.pad_speed").state == "2.0"
    assert hass.states.get("number.pad_speed").state == "2.0"
    assert hass.states.get("switch.pad").state == "on"

    # nobody on it -> pad stops by itself
    statuses[:] = [raw(mode=1, speed=0, t=3)]
    await refresh(hass, entry)
    assert hass.states.get("switch.pad").state == "off"
    assert hass.states.get("sensor.pad_speed").state == "0.0"
    assert coord.update_interval == timedelta(seconds=5)
