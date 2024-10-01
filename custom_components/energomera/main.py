import serial
import serial.tools.list_ports
import time
import re
from typing import Optional, Tuple


def find_port() -> Optional[str]:
    """
    Search for available serial ports and return the first one that matches.
    Returns the port name or None if no suitable port is found.
    """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.device == 'COM2':  # Replace with the correct port if necessary
            return port.device
    return None


def send_receive(ser: serial.Serial, request: bytes, expected_response_len: Optional[int] = None,
                 delay: float = 0.3) -> bytes:
    """
    Send a request to the serial device and receive the response.

    :param ser: The serial connection object.
    :param request: The command to send as a byte sequence.
    :param expected_response_len: The expected length of the response, if known.
    :param delay: Delay time in seconds before reading the response.
    :return: The response from the serial device.
    """
    ser.write(request)
    time.sleep(delay)

    response = ser.read(expected_response_len if expected_response_len else ser.in_waiting)
    return response


def init_serial_connection() -> serial.Serial:
    """
    Initialize and return a serial connection to the meter.
    :return: Serial object for communication.
    """
    serial_port = find_port()
    if not serial_port:
        raise Exception("No valid serial port found.")

    ser = serial.Serial(
        port=serial_port,
        baudrate=9600,  # Communication speed
        parity=serial.PARITY_EVEN,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.SEVENBITS,
        timeout=1  # Read timeout
    )
    return ser


def parse_response(response: bytes) -> None:
    """
    Parse the received response and extract measurement data.
    :param response: The byte string response from the meter.
    """
    global I, P, U, F, T, T1, T2, T_day, T1_day, T2_day, T_month, T1_month, T2_month
    # Convert the response to a string for easier processing
    response_str = response.decode('ascii', errors='ignore')

    # Check if the response contains voltage information
    if "VOLTA" in response_str:
        match = re.search(r'VOLTA\(([\d.]+)\)', response_str)
        if match:
            U = float(match.group(1))
            print(f"Voltage (U): {U} V")

    # Check if the response contains current information
    elif "CURRE" in response_str:
        match = re.search(r'CURRE\(([\d.]+)\)', response_str)
        if match:
            I = float(match.group(1))
            print(f"Current (I): {I} A")

    # Check if the response contains power information
    elif "POWEP" in response_str:
        match = re.search(r'POWEP\(([\d.]+)\)', response_str)
        if match:
            P = float(match.group(1))
            print(f"Power (P): {P} kW")

    # Check if the response contains frequency information
    elif "FREQU" in response_str:
        match = re.search(r'FREQU\(([\d.]+)\)', response_str)
        if match:
            F = float(match.group(1))
            print(f"Frequency (F): {F} Hz")

    # Check if the response contains total energy information (ET0PE)
    elif "ET0PE" in response_str:
        match = re.search(r'ET0PE\(([\d.]+)\)', response_str)
        if match:
            T = float(match.group(1))
            print(f"Total energy (T): {T} kWh")

        # Extract zone energy (T1 and T2)
        zones = re.findall(r'\(([\d.]+)\)', response_str)
        if len(zones) >= 2:
            T1 = float(zones[1])  # Zone 1
            print(f"Energy for zone T1: {T1} kWh")
        if len(zones) >= 3:
            T2 = float(zones[2])  # Zone 2
            print(f"Energy for zone T2: {T2} kWh")

    # Check if the response contains monthly energy information (EAMPE)
    elif "EAMPE" in response_str:
        match = re.search(r'EAMPE\(([\d.]+)\)', response_str)
        if match:
            T_month = float(match.group(1))
            print(f"Energy for the month (T_month): {T_month} kWh")

        # Extract zone energy for the month (T1_month and T2_month)
        zones_month = re.findall(r'\(([\d.]+)\)', response_str)
        if len(zones_month) >= 2:
            T1_month = float(zones_month[1])  # Zone 1 for the month
            print(f"Energy for zone T1 for the month: {T1_month} kWh")
        if len(zones_month) >= 3:
            T2_month = float(zones_month[2])  # Zone 2 for the month
            print(f"Energy for zone T2 for the month: {T2_month} kWh")

    # Check if the response contains daily energy information (EADPE)
    elif "EADPE" in response_str:
        match = re.search(r'EADPE\(([\d.]+)\)', response_str)
        if match:
            T_day = float(match.group(1))
            print(f"Energy for the day (T_day): {T_day} kWh")

        # Extract zone energy for the day (T1_day and T2_day)
        zones_day = re.findall(r'\(([\d.]+)\)', response_str)
        if len(zones_day) >= 2:
            T1_day = float(zones_day[1])  # Zone 1 for the day
            print(f"Energy for zone T1 for the day: {T1_day} kWh")
        if len(zones_day) >= 3:
            T2_day = float(zones_day[2])  # Zone 2 for the day
            print(f"Energy for zone T2 for the day: {T2_day} kWh")


def main() -> None:
    """
    Main function that sends requests to the meter and processes the responses.
    """
    requests: list[Tuple[bytes, int]] = [
        (b'\x2F\x3F\x21\x0D\x0A', 17),  # open session
        (b'\x06\x30\x35\x31\x0D\x0A', 11),  # .051..
        (b'\x01\x50\x31\x02\x28\x37\x37\x37\x37\x37\x37\x29\x03\x21', 1),  # authorization
        (b'\x01\x52\x31\x02\x56\x4F\x4C\x54\x41\x28\x29\x03\x5F', 19),  # .R1.VOLTA(). get voltage
        (b'\x01\x52\x31\x02\x43\x55\x52\x52\x45\x28\x29\x03\x5A', 19),  # .R1.CURRE(). get current
        (b'\x01\x52\x31\x02\x50\x4F\x57\x45\x50\x28\x29\x03\x64', 21),  # .R1.POWEP(). get power
        (b'\x01\x52\x31\x02\x46\x52\x45\x51\x55\x28\x29\x03\x5C', 19),  # .R1.FREQU(). get frequency
        (b'\x01\x52\x31\x02\x45\x54\x30\x50\x45\x28\x29\x03\x37', 64),  # .R1.ET0PE(). get total energy
        (b'\x01\x52\x31\x02\x45\x41\x4D\x50\x45\x28\x30\x39\x2E\x32\x34\x29\x03\x3E', 64),  # .R1.EAMPE(). get energy
        # last month
        (b'\x01\x52\x31\x02\x45\x41\x44\x50\x45\x28\x33\x30\x2E\x30\x39\x2E\x32\x34\x29\x03\x46', 64),  # .R1.EADPE(
        # ). get energy last day
        (b'\x01\x42\x30\x03\x75', 1)  # close session
    ]

    # Initialize the connection
    ser = init_serial_connection()

    try:
        for request, expected_response_len in requests:
            response = send_receive(ser, request, expected_response_len)  # Send the request and receive the response
            parse_response(response)   # Parse and save data from the response
    finally:
        ser.close()


if __name__ == '__main__':
    main()
