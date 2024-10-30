from dataclasses import dataclass, field
from typing import Optional

from .const import START_COMMAND_PREFIX, END_COMMAND_POSTFIX
from datetime import datetime, timedelta


def _calculate_bcc(command_bytes: str) -> int:
    """
    Calculates the checksum (BCC) for the command, starting from the byte after STX (0x02) to ETX (0x03) inclusive.
    Then adds 5 to the least significant byte.
    """
    bcc = 0x00
    for char in command_bytes:
        bcc = (bcc + ord(char)) & 0x7F  # Simple sum with overflow
    return bcc


def generate_command(date_str: str, command: bytes) -> bytes:
    """
    generating command with bcc
    """
    date_bytes = bytes(date_str, 'ascii')
    data_for_count_bcc = START_COMMAND_PREFIX[1:] + command + date_bytes + END_COMMAND_POSTFIX
    bcc_byte = _calculate_bcc(data_for_count_bcc.decode('utf-8'))
    full_command = START_COMMAND_PREFIX + command + date_bytes + END_COMMAND_POSTFIX + bytes([bcc_byte])
    return full_command


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


@dataclass
class DTOEnergy:
    total: Optional[float] = field(default=0)
    t1: Optional[float] = field(default=0)
    t2: Optional[float] = field(default=0)


class DTOEnergyDay(DTOEnergy):
    pass


class DTOEnergyMonthly(DTOEnergy):
    pass


