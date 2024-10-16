import logging
import serial
import time
from datetime import datetime, timedelta
import re
import voluptuous as vol
import serial.tools.list_ports
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_SCAN_INTERVAL,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfFrequency,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

from .services import generate_command
from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PORT,
    CONF_SENSORS,
    CONF_PORT,
    CONF_PRECISION,
    COMMAND_GET_DAILY_ENERGY, COMMAND_GET_MONTHLY_ENERGY,
)

_LOGGER = logging.getLogger(__name__)

# types sensors and commands
SENSOR_TYPES = {
    "voltage": {
        "name": "Voltage",
        "command": b'\x01\x52\x31\x02\x56\x4F\x4C\x54\x41\x28\x29\x03\x5F',
        "regex": r'VOLTA\(([\d.]+)\)',
        "unit": UnitOfElectricPotential.VOLT,
        "device_class": SensorDeviceClass.VOLTAGE,
    },
    "current": {
        "name": "Current",
        "command": b'\x01\x52\x31\x02\x43\x55\x52\x52\x45\x28\x29\x03\x5A',
        "regex": r'CURRE\(([\d.]+)\)',
        "unit": UnitOfElectricCurrent.AMPERE,
        "device_class": SensorDeviceClass.CURRENT,
    },
    "power": {
        "name": "Power",
        "command": b'\x01\x52\x31\x02\x50\x4F\x57\x45\x50\x28\x29\x03\x64',
        "regex": r'POWEP\(([\d.]+)\)',
        "unit": UnitOfPower.KILO_WATT,
        "device_class": SensorDeviceClass.POWER,
    },
    "frequency": {
        "name": "Frequency",
        "command": b'\x01\x52\x31\x02\x46\x52\x45\x51\x55\x28\x29\x03\x5C',
        "regex": r'FREQU\(([\d.]+)\)',
        "unit": UnitOfFrequency.HERTZ,
        "device_class": SensorDeviceClass.FREQUENCY,
    },
    "total_energy": {
        "name": "Total Energy",
        "command": b'\x01\x52\x31\x02\x45\x54\x30\x50\x45\x28\x29\x03\x37',
        "regex": r'ET0PE\(([\d.]+)\)',
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
    },
    "day_energy": {
        "name": "Energomera last day energy",
        "command": b'',  # Команда будет динамически изменена в коде
        "regex": r'EADPE\(([\d.]+)\)',  # Регулярное выражение для обработки ответа
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
    },
    "monthly_energy": {
        "name": "Energomera last month energy",
        "command": b'',  # Команда будет динамически изменена в коде
        "regex": r'EAMPE\(([\d.]+)\)',  # Регулярное выражение для обработки ответа
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
    },
}

SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required("type"): vol.In(SENSOR_TYPES.keys()),
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional("friendly_name"): cv.string,
        vol.Optional("unique_id"): cv.string,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
        vol.Optional(CONF_PRECISION, default=2): cv.positive_int,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.string,
        vol.Required(CONF_SENSORS): vol.All(cv.ensure_list, [SENSOR_SCHEMA]),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities,
        discovery_info=None,
):
    """Set up the Energomera Meter sensor platform."""
    port = config[CONF_PORT]
    scan_interval = config[CONF_SCAN_INTERVAL]
    sensors = config[CONF_SENSORS]

    meter = MeterConnection(port)
    entities = []
    for sensor_conf in sensors:
        sensor_type = sensor_conf["type"]
        sensor_info = SENSOR_TYPES[sensor_type]

        name = sensor_conf.get(CONF_NAME, sensor_info["name"])
        friendly_name = sensor_conf.get("friendly_name", name)
        unique_id = sensor_conf.get("unique_id")
        unit = sensor_conf.get(CONF_UNIT_OF_MEASUREMENT, sensor_info["unit"])
        device_class = sensor_info["device_class"]
        state_class = SensorStateClass.MEASUREMENT
        precision = sensor_conf.get(CONF_PRECISION)

        entities.append(
            EnergomeraSensor(
                meter,
                name,
                friendly_name,
                unique_id,
                sensor_info["command"],
                sensor_info["regex"],
                unit,
                device_class,
                state_class,
                precision,
            )
        )

    async_add_entities(entities)

    async def async_update_data(now):
        """Fetch data from the meter."""
        await hass.async_add_executor_job(meter.update, entities)

    # Schedule updates
    async_track_time_interval(hass, async_update_data, scan_interval)


def get_prev_day():
    """Get the previous day."""
    today = datetime.today()
    previous_day = today - timedelta(days=1)
    previous_day_str = previous_day.strftime('%d.%m.%y')
    return previous_day_str


def get_prev_month():
    """Get the previous month."""
    today = datetime.today()
    first_day_of_prev_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_prev_month - timedelta(days=1)
    previous_month = last_day_of_previous_month.strftime('%m.%y')
    return previous_month


class EnergomeraSensor(SensorEntity):
    """Representation of a Energomera Sensor."""

    def __init__(
            self,
            meter,
            name,
            friendly_name,
            unique_id,
            command,
            regex,
            unit,
            device_class,
            state_class,
            precision,
    ):
        """Initialize the sensor."""
        self._meter = meter
        self._name = name
        self._friendly_name = friendly_name
        self._unique_id = unique_id
        self._command = command
        self._regex = regex
        self._unit = unit
        self._device_class = device_class
        self._state_class = state_class
        self._precision = precision
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def friendly_name(self):
        """Return the friendly name of the sensor."""
        return self._friendly_name

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    @property
    def state_class(self):
        """Return the state class."""
        return self._state_class

    def update(self, open_session=False):
        """Fetch new state data for the sensor."""
        if self._name == "Energomera last month energy":
            prev_month = get_prev_month()
            if prev_month:
                self._command = generate_command(prev_month, COMMAND_GET_MONTHLY_ENERGY)
            else:
                _LOGGER.warning(f"Could not retrieve current month for sensor {self._name}")
                return
        elif self._name == "Energomera last day energy":
            prev_day = get_prev_day()
            if prev_day:
                self._command = generate_command(prev_day, COMMAND_GET_DAILY_ENERGY)

        response = self._meter.send_command(self._command)
        if response:
            match = re.search(self._regex, response)
            if match:
                self._state = round(float(match.group(1)), self._precision)
            else:
                _LOGGER.warning("No matching data for sensor %s", self._name)
        else:
            _LOGGER.warning("No response for sensor %s", self._name)


class MeterConnection:
    """Handle communication with the Energomera meter."""
    state_session = False

    def __init__(self, port):
        self.port = port
        self.serial_conn = self.init_serial_connection()

    def init_serial_connection(self):
        """Initialize serial connection to the meter."""
        try:
            ser = serial.Serial(
                port=self.port,
                baudrate=9600,
                bytesize=serial.SEVENBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=2
            )
            return ser
        except serial.SerialException as e:
            _LOGGER.error("Error opening serial port %s: %s", self.port, e)
            return None

    def send_command(self, command, expected_len=100):
        """Send a command to the meter and return the response."""
        if not self.serial_conn:
            return None

        try:
            self.serial_conn.write(command)
            time.sleep(0.3)  # Небольшая задержка для получения ответа
            response = self.serial_conn.read(expected_len).decode('ascii')
            _LOGGER.debug(f'Sent command: {command}')
            _LOGGER.debug(f'Received response: {response}')
            return response
        except serial.SerialTimeoutException:
            _LOGGER.error("Timeout communicating with meter")
            return None

    def send_command(self, command, expected_len=100):
        """Send a command to the meter and return the response."""
        if not self.serial_conn or not self.serial_conn.is_open:
            _LOGGER.error("Serial connection is not open or available.")
            return None

        try:
            self.serial_conn.write(command)
            time.sleep(0.3)  # Небольшая задержка для получения ответа
            response = self.serial_conn.read(expected_len)
            if response:
                return response.decode('ascii')
            else:
                _LOGGER.warning("No data received from the meter.")
                return None
        except serial.SerialException as e:
            _LOGGER.error(f"Error communicating with the meter: {e}")
            return None

    def execute_open_session(self):
        """Open the session with the meter and authenticate."""
        _LOGGER.debug("Opening session with the meter")

        # Закрываем порт, если он уже открыт
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            time.sleep(1)

        # Пытаемся снова открыть соединение
        self.serial_conn.open()

        requests = [
            (b'\x2F\x3F\x21\x0D\x0A', 17),  # Open session
            (b'\x06\x30\x35\x31\x0D\x0A', 11),  # .051..
            (b'\x01\x50\x31\x02\x28\x37\x37\x37\x37\x37\x37\x29\x03\x21', 1),  # Auth
        ]
        for command, expected_len in requests:
            response = self.send_command(command, expected_len)
            if response == '\x06':
                self.state_session = True
            else:
                self.state_session = False

    def execute_close_session(self):
        """Close the session with the meter."""
        _LOGGER.debug("Closing session with the meter")
        if self.serial_conn and self.serial_conn.is_open:
            command = b'\x01\x42\x30\x03\x75'  # Close session
            self.send_command(command, 1)
            self.serial_conn.close()

    def update(self, sensors):
        """Open session, fetch data from all sensors, and close session."""
        self.execute_open_session()

        if self.state_session:
            for sensor in sensors:
                sensor.update(open_session=True)

        self.execute_close_session()
