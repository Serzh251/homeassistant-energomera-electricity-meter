from .const import START_COMMAND_PREFIX, END_COMMAND_POSTFIX


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
