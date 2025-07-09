import logging
import asyncio
import aiohttp
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    coordinator = BazziteWebSocketCoordinator(hass, entry)
    await coordinator.start()

    async_add_entities([
        BazziteGameSensor(coordinator),
        BazziteCPUTemperatureSensor(coordinator)
    ])

class BazziteWebSocketCoordinator:
    def __init__(self, hass, entry):
        self.hass = hass
        self.config = entry.data
        self.data = {}
        self.listeners = []
        self.ws_task = None

    async def start(self):
        self.ws_task = asyncio.create_task(self._connect_websocket())

    async def _connect_websocket(self):
        session = async_get_clientsession(self.hass)
        url = f"ws://{self.config['host']}:{self.config['port']}/ws"
        while True:
            try:
                _LOGGER.info(f"Connecting to Bazzite WebSocket at {url}")
                async with session.ws_connect(url) as ws:
                    _LOGGER.info("Bazzite WebSocket connected!")
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            new_data = msg.json()
                            _LOGGER.debug("WebSocket message received: %s", new_data)
                            self.data.update(new_data)
                            self._notify_listeners()
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.error("WebSocket error: %s", msg.data)
                            break
            except Exception as e:
                _LOGGER.error("WebSocket connection error: %s", e)
            await asyncio.sleep(5)  # Retry delay

    def _notify_listeners(self):
        for update_callback in self.listeners:
            update_callback()

    def async_add_listener(self, update_callback):
        self.listeners.append(update_callback)

class BazziteGameSensor(Entity):
    def __init__(self, coordinator: BazziteWebSocketCoordinator):
        self.coordinator = coordinator
        self._attr_name = "Bazzite Current Game"
        self._attr_unique_id = "bazzite_current_game"
        
        coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def should_poll(self):
        return False

    @property
    def state(self):
        return self.coordinator.data.get("status", None)
        
    @property
    def available(self):
        return "status" in self.coordinator.data

    @property
    def icon(self):
        state = self.state
        if state == "idle":
            return "mdi:power-standby"
        if state == "unavailable":
            return "mdi:alert-circle-outline"
        return "mdi:controller-classic"

class BazziteCPUTemperatureSensor(Entity):
    def __init__(self, coordinator: BazziteWebSocketCoordinator):
        self.coordinator = coordinator
        self._attr_name = "Bazzite CPU Temperature"
        self._attr_unique_id = "bazzite_cpu_temperature"
        self._attr_device_class = "temperature"
        self._attr_unit_of_measurement = "°C"
        self._attr_icon = "mdi:thermometer"

        coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def should_poll(self):
        return False

    @property
    def state(self):
        return self.coordinator.data.get("cpu_temperature", None)
        
    @property
    def available(self):
        return "cpu_temperature" in self.coordinator.data