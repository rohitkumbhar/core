"""Test for the LCN switch platform."""
from unittest.mock import patch

from pypck.inputs import ModStatusOutput, ModStatusRelays
from pypck.lcn_addr import LcnAddr
from pypck.lcn_defs import RelayStateModifier

from homeassistant.components.lcn.helpers import get_device_connection
from homeassistant.components.switch import DOMAIN as DOMAIN_SWITCH
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.helpers import entity_registry as er

from .conftest import MockModuleConnection


async def test_setup_lcn_switch(hass, lcn_connection):
    """Test the setup of switch."""
    for entity_id in (
        "switch.switch_output1",
        "switch.switch_output2",
        "switch.switch_relay1",
        "switch.switch_relay2",
    ):
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_OFF


async def test_entity_attributes(hass, entry, lcn_connection):
    """Test the attributes of an entity."""
    entity_registry = er.async_get(hass)

    entity_output = entity_registry.async_get("switch.switch_output1")

    assert entity_output
    assert entity_output.unique_id == f"{entry.entry_id}-m000007-output1"
    assert entity_output.original_name == "Switch_Output1"

    entity_relay = entity_registry.async_get("switch.switch_relay1")

    assert entity_relay
    assert entity_relay.unique_id == f"{entry.entry_id}-m000007-relay1"
    assert entity_relay.original_name == "Switch_Relay1"


@patch.object(MockModuleConnection, "dim_output")
async def test_output_turn_on(dim_output, hass, lcn_connection):
    """Test the output switch turns on."""
    # command failed
    dim_output.return_value = False

    await hass.services.async_call(
        DOMAIN_SWITCH,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.switch_output1"},
        blocking=True,
    )
    await hass.async_block_till_done()
    dim_output.assert_awaited_with(0, 100, 0)

    state = hass.states.get("switch.switch_output1")
    assert state.state == STATE_OFF

    # command success
    dim_output.reset_mock(return_value=True)
    dim_output.return_value = True

    await hass.services.async_call(
        DOMAIN_SWITCH,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.switch_output1"},
        blocking=True,
    )
    await hass.async_block_till_done()
    dim_output.assert_awaited_with(0, 100, 0)

    state = hass.states.get("switch.switch_output1")
    assert state.state == STATE_ON


@patch.object(MockModuleConnection, "dim_output")
async def test_output_turn_off(dim_output, hass, lcn_connection):
    """Test the output switch turns off."""
    state = hass.states.get("switch.switch_output1")
    state.state = STATE_ON

    # command failed
    dim_output.return_value = False

    await hass.services.async_call(
        DOMAIN_SWITCH,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.switch_output1"},
        blocking=True,
    )
    await hass.async_block_till_done()
    dim_output.assert_awaited_with(0, 0, 0)

    state = hass.states.get("switch.switch_output1")
    assert state.state == STATE_ON

    # command success
    dim_output.reset_mock(return_value=True)
    dim_output.return_value = True

    await hass.services.async_call(
        DOMAIN_SWITCH,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.switch_output1"},
        blocking=True,
    )
    await hass.async_block_till_done()
    dim_output.assert_awaited_with(0, 0, 0)

    state = hass.states.get("switch.switch_output1")
    assert state.state == STATE_OFF


@patch.object(MockModuleConnection, "control_relays")
async def test_relay_turn_on(control_relays, hass, lcn_connection):
    """Test the relay switch turns on."""
    states = [RelayStateModifier.NOCHANGE] * 8
    states[0] = RelayStateModifier.ON

    # command failed
    control_relays.return_value = False

    await hass.services.async_call(
        DOMAIN_SWITCH,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.switch_relay1"},
        blocking=True,
    )
    await hass.async_block_till_done()
    control_relays.assert_awaited_with(states)

    state = hass.states.get("switch.switch_relay1")
    assert state.state == STATE_OFF

    # command success
    control_relays.reset_mock(return_value=True)
    control_relays.return_value = True

    await hass.services.async_call(
        DOMAIN_SWITCH,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.switch_relay1"},
        blocking=True,
    )
    await hass.async_block_till_done()
    control_relays.assert_awaited_with(states)

    state = hass.states.get("switch.switch_relay1")
    assert state.state == STATE_ON


@patch.object(MockModuleConnection, "control_relays")
async def test_relay_turn_off(control_relays, hass, lcn_connection):
    """Test the relay switch turns off."""
    states = [RelayStateModifier.NOCHANGE] * 8
    states[0] = RelayStateModifier.OFF

    state = hass.states.get("switch.switch_relay1")
    state.state = STATE_ON

    # command failed
    control_relays.return_value = False

    await hass.services.async_call(
        DOMAIN_SWITCH,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.switch_relay1"},
        blocking=True,
    )
    await hass.async_block_till_done()
    control_relays.assert_awaited_with(states)

    state = hass.states.get("switch.switch_relay1")
    assert state.state == STATE_ON

    # command success
    control_relays.reset_mock(return_value=True)
    control_relays.return_value = True

    await hass.services.async_call(
        DOMAIN_SWITCH,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.switch_relay1"},
        blocking=True,
    )
    await hass.async_block_till_done()
    control_relays.assert_awaited_with(states)

    state = hass.states.get("switch.switch_relay1")
    assert state.state == STATE_OFF


async def test_pushed_output_status_change(hass, entry, lcn_connection):
    """Test the output switch changes its state on status received."""
    device_connection = get_device_connection(hass, (0, 7, False), entry)
    address = LcnAddr(0, 7, False)

    # push status "on"
    inp = ModStatusOutput(address, 0, 100)
    await device_connection.async_process_input(inp)
    await hass.async_block_till_done()

    state = hass.states.get("switch.switch_output1")
    assert state.state == STATE_ON

    # push status "off"
    inp = ModStatusOutput(address, 0, 0)
    await device_connection.async_process_input(inp)
    await hass.async_block_till_done()

    state = hass.states.get("switch.switch_output1")
    assert state.state == STATE_OFF


async def test_pushed_relay_status_change(hass, entry, lcn_connection):
    """Test the relay switch changes its state on status received."""
    device_connection = get_device_connection(hass, (0, 7, False), entry)
    address = LcnAddr(0, 7, False)
    states = [False] * 8

    # push status "on"
    states[0] = True
    inp = ModStatusRelays(address, states)
    await device_connection.async_process_input(inp)
    await hass.async_block_till_done()

    state = hass.states.get("switch.switch_relay1")
    assert state.state == STATE_ON

    # push status "off"
    states[0] = False
    inp = ModStatusRelays(address, states)
    await device_connection.async_process_input(inp)
    await hass.async_block_till_done()

    state = hass.states.get("switch.switch_relay1")
    assert state.state == STATE_OFF


async def test_unload_config_entry(hass, entry, lcn_connection):
    """Test the switch is removed when the config entry is unloaded."""
    await hass.config_entries.async_unload(entry.entry_id)
    assert hass.states.get("switch.switch_output1").state == STATE_UNAVAILABLE
