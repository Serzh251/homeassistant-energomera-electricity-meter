# from homeassistant.core import HomeAssistant
#
# DOMAIN = "energomera"
#
#
# async def async_setup(hass: HomeAssistant, config: dict):
#     """Set up the Energomera component."""
#     hass.states.async_set(f"{DOMAIN}.state", "initialized")
#     return True  # return True, if integration setup success

from homeassistant.helpers import discovery

DOMAIN = "energomera"


def setup(hass, config):
    """Set up the integration."""
    discovery.load_platform(hass, "sensor", DOMAIN, {}, config)
    return True
