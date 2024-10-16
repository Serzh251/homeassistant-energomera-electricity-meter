from typing import Final

DOMAIN = "energomera"
DEFAULT_SCAN_INTERVAL = 60  # Default polling interval in seconds
CONF_NAME: Final = "name"

DEFAULT_PORT = "/dev/ttyUSB0"

CONF_SENSORS = "sensors"
CONF_PORT = "port"
CONF_UNIT = "unit_of_measurement"
CONF_DEVICE_CLASS = "device_class"
CONF_STATE_CLASS = "state_class"
CONF_PRECISION = "precision"

START_COMMAND_PREFIX = b'\x01\x52\x31\x02'  # SOH R1 STX
COMMAND_GET_DAILY_ENERGY = b'\x45\x41\x44\x50\x45\x28'  # EADPE(
COMMAND_GET_MONTHLY_ENERGY = b'\x45\x41\x4D\x50\x45\x28'  # EAMPE(
END_COMMAND_POSTFIX = b'\x29\x03'  # ) ETH
