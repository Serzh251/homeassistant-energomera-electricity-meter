import logging
import serial
import time
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
import re
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Example sensor entity to handle meter data
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the sensor platform."""
    scan_interval = config.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    meter = MeterConnection()
    sensors = [
        MeterSensor(meter, "Voltage_energomera", "U", "V", "mdi:flash"),
        MeterSensor(meter, "Current_energomera", "I", "A", "mdi:current-ac"),
        MeterSensor(meter, "Power_energomera", "P", "kW", "mdi:power"),
        MeterSensor(meter, "Frequency_energomera", "F", "Hz", "mdi:sine-wave"),
        MeterSensor(meter, "Total Energy_energomera", "T", "kWh", "mdi:counter"),
    ]

    async_add_entities(sensors)

    async def update_data(event_time):
        """Fetch new data from the meter and update sensors."""
        meter.update()
        for sensor in sensors:
            sensor.async_schedule_update_ha_state(True)

    # Schedule periodic updates
    async_track_time_interval(hass, update_data, timedelta(seconds=scan_interval))


class MeterSensor(Entity):
    """Representation of a Meter Sensor."""

    def __init__(self, meter, name, attr, unit, icon):
        """Initialize the sensor."""
        self._meter = meter
        self._name = name
        self._attr = attr
        self._state = None
        self._unit = unit
        self._icon = icon

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return getattr(self._meter, self._attr, None)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    def update(self):
        """Fetch data from the meter."""
        self._meter.update()


class MeterConnection:
    """Handle connection to the meter and retrieve data."""

    def __init__(self):
        self.U = None  # Voltage
        self.I = None  # Current
        self.P = None  # Power
        self.F = None  # Frequency
        self.T = None  # Total energy

        self.serial_conn = self.init_serial_connection()

    def init_serial_connection(self):
        """Initialize and return a serial connection to the meter."""
        serial_port = self.find_port()
        if not serial_port:
            raise Exception("No valid serial port found.")
        ser = serial.Serial(
            port=serial_port,
            baudrate=9600,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.SEVENBITS,
            timeout=1
        )
        return ser

    def find_port(self):
        """Find and return the correct serial port."""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # if port.device == 'COM2':  # Adjust this to match your setup
            return port.device
        return None

    def update(self):
        """Update the meter data by sending requests and receiving responses."""
        requests = [
            (b'\x2F\x3F\x21\x0D\x0A', 17),  # Open session
            (b'\x06\x30\x35\x31\x0D\x0A', 11),  # .051..
            (b'\x01\x50\x31\x02\x28\x37\x37\x37\x37\x37\x37\x29\x03\x21', 1),  # Auth
            (b'\x01\x52\x31\x02\x56\x4F\x4C\x54\x41\x28\x29\x03\x5F', 19),  # Voltage
            (b'\x01\x52\x31\x02\x43\x55\x52\x52\x45\x28\x29\x03\x5A', 19),  # Current
            (b'\x01\x52\x31\x02\x50\x4F\x57\x45\x50\x28\x29\x03\x64', 21),  # Power
            (b'\x01\x52\x31\x02\x46\x52\x45\x51\x55\x28\x29\x03\x5C', 19),  # Frequency
            (b'\x01\x52\x31\x02\x45\x54\x30\x50\x45\x28\x29\x03\x37', 64),  # Total energy
            (b'\x01\x42\x30\x03\x75', 1),  # Close session
        ]

        for request, expected_len in requests:
            response = self.send_receive(self.serial_conn, request, expected_len)
            self.parse_response(response)

    def send_receive(self, ser, request, expected_len):
        """Send a request to the meter and receive the response."""
        ser.write(request)
        time.sleep(0.3)
        return ser.read(expected_len)

    def parse_response(self, response):
        """Parse the received response and extract measurement data."""
        response_str = response.decode('ascii', errors='ignore')
        if "VOLTA" in response_str:
            match = re.search(r'VOLTA\(([\d.]+)\)', response_str)
            if match:
                self.U = float(match.group(1))
        elif "CURRE" in response_str:
            match = re.search(r'CURRE\(([\d.]+)\)', response_str)
            if match:
                self.I = float(match.group(1))
        elif "POWEP" in response_str:
            match = re.search(r'POWEP\(([\d.]+)\)', response_str)
            if match:
                self.P = float(match.group(1))
        elif "FREQU" in response_str:
            match = re.search(r'FREQU\(([\d.]+)\)', response_str)
            if match:
                self.F = float(match.group(1))
        elif "ET0PE" in response_str:
            match = re.search(r'ET0PE\(([\d.]+)\)', response_str)
            if match:
                self.T = float(match.group(1))
