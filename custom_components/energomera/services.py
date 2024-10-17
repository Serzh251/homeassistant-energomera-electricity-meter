from .const import START_COMMAND_PREFIX, END_COMMAND_POSTFIX
from datetime import datetime, timedelta

def _calculate_bcc(command_bytes: bytes) -> int:
    """
    Calculates the checksum (BCC) for the command, starting from the byte after STX (0x02) to ETX (0x03) inclusive.
    Then adds 5 to the least significant byte.
    """
    bcc_sum = sum(command_bytes)
    bcc = bcc_sum & 0xFF  # take the least significant byte of the sum
    bcc = (bcc + 5) & 0xFF  # Add 5 (according to the identified pattern)
    return bcc


def generate_command(date_str: str, command: bytes) -> bytes:
    """
    generating command with bcc
    """
    date_bytes = bytes(date_str, 'ascii')
    full_command = command + date_bytes + END_COMMAND_POSTFIX  # data for calculate bcc

    bcc_byte = _calculate_bcc(full_command)
    return START_COMMAND_PREFIX + full_command + bytes([bcc_byte])


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
