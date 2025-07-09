import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_send_command(call):
        command = call.data.get("command")
        await send_command_to_bazzite(hass, entry.data, command)

    hass.services.async_register(DOMAIN, "send_command", handle_send_command)
    return True

async def send_command_to_bazzite(hass, config, command):
    session = async_get_clientsession(hass)
    url = f"http://{config['host']}:{config['port']}/command"
    async with session.post(url, json={"command": command}) as resp:
        return await resp.text()
        
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True