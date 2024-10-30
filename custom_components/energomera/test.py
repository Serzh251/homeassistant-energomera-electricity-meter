import time
import serial

# RS485 settings
RS485_BAUDRATE = 9600
RS485_DATABITS = serial.SEVENBITS
RS485_PARITY = serial.PARITY_EVEN
RS485_STOPBITS = serial.STOPBITS_ONE
RS485_PORT = '/dev/ttyUSB0'  # Replace with your actual serial port

# Meter polling parameters
CE102M_Addr = ""  # Address ("" for non-addressed)
CE102M_CyclePeriod = 10000
CE102M_RequestPeriod = 1000
ce102m_params = ["VOLTA", "CURRE", "POWEP", "COS_f", "FREQU"]

# Serial communication setup
ser = None
last_param_name = None  # To store the name of the last parameter requested


# Connect to RS485
def rs485_connect():
    global ser
    ser = serial.Serial(
        port=RS485_PORT,
        baudrate=RS485_BAUDRATE,
        bytesize=RS485_DATABITS,
        parity=RS485_PARITY,
        stopbits=RS485_STOPBITS,
        timeout=1
    )
    if ser.is_open:
        print(f"Connected to RS485 on {RS485_PORT}")
    else:
        print("Failed to connect to RS485.")


# Calculate BCC checksum
def process_bcc(aData):
    bcc = 0x00
    for char in aData:
        bcc = (bcc + ord(char)) & 0x7F  # Simple sum with overflow
    return bcc


# Handle incoming RS485 data
def handle_rx(rx_buff):
    global last_param_name
    if len(rx_buff) == 0 or ord(rx_buff[0]) != 0x02:
        return  # Check if valid packet
    bcc = process_bcc(rx_buff[1:-1])
    if ord(rx_buff[-1]) != bcc:
        print("Checksum failed.")
        return  # Checksum failed
    if last_param_name is not None and last_param_name in rx_buff:
        start = rx_buff.index(last_param_name) + len(last_param_name) + 1
        end = rx_buff.index(")", start)
        param_value = rx_buff[start:end]
        print(f"{last_param_name}: {param_value}")
        return param_value


# Send data via RS485
def rs485_send(packet):
    global ser
    if ser is not None and ser.is_open:
        ser.write(packet)
        time.sleep(len(packet) * 0.001)  # Delay based on packet length
    else:
        print("RS485 port is not open.")


# Start connection with the meter
def ce102m_start(addr=""):
    rs485_send(f"/?{addr}!\r\n".encode())


# Ask meter for its ID
def ce102m_p0():
    rs485_send("\x06\x30\x35\x31\r\n".encode())


# Request parameter from meter
def ce102m_get_param(param_name):
    global last_param_name
    request = f"\x01R1\x02{param_name}()\x03"
    bcc = chr(process_bcc(request[1:]))
    request += bcc
    rs485_send(request.encode())
    last_param_name = param_name  # Store the name of the last parameter requested


# Stop communication with the meter
def ce102m_stop():
    rs485_send("\x01\x42\x30\x03\x75".encode())


# Main loop to send requests
def next_request():
    for step, param in enumerate(ce102m_params, start=1):
        if step == 1:
            ce102m_start(CE102M_Addr)
        elif step == 2:
            ce102m_p0()
        elif step == len(ce102m_params) + 3:
            ce102m_stop()
        else:
            ce102m_get_param(param)
        time.sleep(CE102M_RequestPeriod / 1000.0)


# Main script setup
# rs485_connect()
#
# last_cycle_time = time.time()
# while True:
#     current_time = time.time()
#     if (current_time - last_cycle_time) > (CE102M_CyclePeriod / 1000.0):
#         next_request()
#         last_cycle_time = current_time
#
#     # Check if data is available in RS485 buffer
#     if ser.in_waiting > 0:
#         rx_buff = ser.read(ser.in_waiting).decode('ascii')
#         handle_rx(rx_buff)
#
#     time.sleep(0.1)
param_name= 'EADPE(23.09.24)'
request = f"\x01R1\x02{param_name}\x03"
bcc = process_bcc(request[1:])