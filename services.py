from dataclasses import dataclass, field
from typing import Optional

from .const import START_COMMAND_PREFIX, END_COMMAND_POSTFIX
from datetime import datetime, timedelta


def _calculate_bcc(command_bytes: str) -> int:
    """
    Calculates the checksum (BCC) for the command, starting from the byte after STX (0x02) to ETX (0x03) inclusive.
    according ГОСТ Р МЭК 61107-2001
    """
    bcc = 0x00
    for char in command_bytes:
        bcc = (bcc + ord(char)) & 0x7F
    return bcc


def generate_command(date_str: str, command: bytes) -> bytes:
    """
    generating command with bcc
    """
    date_bytes = bytes(date_str, 'ascii')
    data_for_count_bcc = START_COMMAND_PREFIX[1:] + command + date_bytes + END_COMMAND_POSTFIX
    bcc_byte = _calculate_bcc(data_for_count_bcc.decode('utf-8'))
    return START_COMMAND_PREFIX + command + date_bytes + END_COMMAND_POSTFIX + bytes([bcc_byte])



def get_prev_day():
    today = datetime.today()
    previous_day = today - timedelta(days=1)
    return previous_day.strftime('%d.%m.%y')


def get_prev_month():
    today = datetime.today()
    first_day_of_prev_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_prev_month - timedelta(days=1)
    return last_day_of_previous_month.strftime('%m.%y')


@dataclass
class DTOEnergy:
    total: Optional[float] = field(default=0)
    t1: Optional[float] = field(default=0)
    t2: Optional[float] = field(default=0)


class DTOEnergyDay(DTOEnergy):
    pass


class DTOEnergyMonthly(DTOEnergy):
    pass


