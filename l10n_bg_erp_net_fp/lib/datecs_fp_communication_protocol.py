#!/usr/bin/env python3
"""
Datecs Fiscal Printer Communication Protocol v2.11
Python implementation for communication with Datecs fiscal devices.
"""

import serial
import time
import logging
from typing import List, Optional, Tuple, Union, Dict
from dataclasses import dataclass
from enum import IntEnum


class DatecsError(Exception):
    """Custom exception for Datecs communication errors"""
    pass


class DatecsTimeoutError(DatecsError):
    """Timeout error for Datecs communication"""
    pass


class FiscalDeviceStatus:
    """Status byte interpretation for Datecs fiscal devices"""

    def __init__(self, status_bytes: bytes):
        self.status_bytes = status_bytes
        self.bits = []

        # Convert each byte to 8 bits
        for byte in status_bytes:
            bits = []
            for i in range(8):
                bits.append((byte >> i) & 1)
            self.bits.extend(bits)

    @property
    def cover_open(self) -> bool:
        """Cover is open"""
        return bool(self.bits[6])  # Byte 0, Bit 6

    @property
    def general_error(self) -> bool:
        """General error"""
        return bool(self.bits[5])  # Byte 0, Bit 5

    @property
    def printer_failure(self) -> bool:
        """Printing mechanism failure"""
        return bool(self.bits[4])  # Byte 0, Bit 4

    @property
    def rtc_not_synchronized(self) -> bool:
        """Real time clock not synchronized"""
        return bool(self.bits[2])  # Byte 0, Bit 2

    @property
    def invalid_command(self) -> bool:
        """Invalid command code"""
        return bool(self.bits[1])  # Byte 0, Bit 1

    @property
    def syntax_error(self) -> bool:
        """Syntax error"""
        return bool(self.bits[0])  # Byte 0, Bit 0

    @property
    def non_fiscal_receipt_open(self) -> bool:
        """Non-fiscal receipt is open"""
        return bool(self.bits[21])  # Byte 2, Bit 5

    @property
    def ej_nearly_full(self) -> bool:
        """EJ nearly full"""
        return bool(self.bits[20])  # Byte 2, Bit 4

    @property
    def fiscal_receipt_open(self) -> bool:
        """Fiscal receipt is open"""
        return bool(self.bits[19])  # Byte 2, Bit 3

    @property
    def ej_full(self) -> bool:
        """EJ is full"""
        return bool(self.bits[18])  # Byte 2, Bit 2

    @property
    def near_paper_end(self) -> bool:
        """Near paper end"""
        return bool(self.bits[17])  # Byte 2, Bit 1

    @property
    def end_of_paper(self) -> bool:
        """End of paper"""
        return bool(self.bits[16])  # Byte 2, Bit 0

    @property
    def fiscal_memory_damaged(self) -> bool:
        """Fiscal memory is damaged"""
        return bool(self.bits[38])  # Byte 4, Bit 6

    @property
    def fiscal_memory_full(self) -> bool:
        """Fiscal memory is full"""
        return bool(self.bits[36])  # Byte 4, Bit 4

    @property
    def device_fiscalized(self) -> bool:
        """Device is fiscalized"""
        return bool(self.bits[43])  # Byte 5, Bit 3


@dataclass
class DatecsResponse:
    """Response structure from Datecs device"""
    error_code: int
    data: List[str]
    status: FiscalDeviceStatus
    raw_message: bytes


class DatecsProtocol:
    """
    Datecs fiscal printer communication protocol implementation

    This class implements the low-level communication protocol for Datecs
    fiscal devices as specified in the programmer's manual v2.11.
    """

    # Protocol constants
    PRE = 0x01  # Preamble
    PST = 0x05  # Postamble
    SEP = 0x04  # Separator
    EOT = 0x03  # Terminator
    NAK = 0x15  # Negative acknowledgment
    SYN = 0x16  # Synchronous idle

    # Default timeouts
    DEFAULT_TIMEOUT = 0.5  # 500ms as per specification
    SYN_TIMEOUT = 0.06  # 60ms SYN timeout

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize Datecs protocol

        Args:
            port: Serial port (e.g. 'COM1' or '/dev/ttyUSB0')
            baudrate: Communication speed (default 115200)
            timeout: Response timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.sequence = 0x20  # Starting sequence number
        self.serial_conn: Optional[serial.Serial] = None

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def connect(self) -> None:
        """Establish serial connection to device"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            self.logger.info(f"Connected to {self.port} at {self.baudrate} baud")
        except serial.SerialException as e:
            raise DatecsError(f"Failed to connect to {self.port}: {e}")

    def disconnect(self) -> None:
        """Close serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.logger.info("Disconnected from device")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def _ascii_hex_encode(self, value: int, length: int) -> bytes:
        """Convert integer to ASCII-hex format as required by protocol"""
        hex_str = f"{value:0{length}X}"
        return bytes([ord(c) + 0x30 for c in hex_str])

    def _ascii_hex_decode(self, data: bytes) -> int:
        """Decode ASCII-hex format to integer"""
        hex_str = ''.join([chr(b - 0x30) for b in data])
        return int(hex_str, 16)

    def _calculate_bcc(self, data: bytes) -> int:
        """Calculate block check character (BCC) - simple sum"""
        return sum(data) & 0xFFFF

    def _build_message(self, command: int, data: str = "") -> bytes:
        """
        Build a complete message frame

        Args:
            command: Command code (0-255)
            data: Command data string

        Returns:
            Complete message frame as bytes
        """
        data_bytes = data.encode('cp1251') if data else b''

        # Build message without BCC first
        message_parts = [
            self._ascii_hex_encode(len(data_bytes) + 10 + 0x20, 4),  # LEN
            bytes([self.sequence]),  # SEQ
            self._ascii_hex_encode(command, 4),  # CMD
            data_bytes,  # DATA
            bytes([self.PST])  # PST
        ]

        # Calculate message length for BCC calculation
        message_for_bcc = b''.join(message_parts)

        # Calculate and append BCC
        bcc = self._calculate_bcc(message_for_bcc)
        message_parts.append(self._ascii_hex_encode(bcc, 4))

        # Complete message with preamble and terminator
        complete_message = (
            bytes([self.PRE]) +
            b''.join(message_parts) +
            bytes([self.EOT])
        )

        return complete_message

    def _parse_response(self, response: bytes) -> DatecsResponse:
        """
        Parse response message from device

        Args:
            response: Raw response bytes

        Returns:
            Parsed response object
        """
        if len(response) < 15:  # Minimum message length
            raise DatecsError("Response too short")

        if response[0] != self.PRE:
            raise DatecsError("Invalid preamble")

        if response[-1] != self.EOT:
            raise DatecsError("Invalid terminator")

        # Extract message length
        msg_len = self._ascii_hex_decode(response[1:5]) - 0x20

        # Extract command echo
        cmd_echo = self._ascii_hex_decode(response[6:10])

        # Find separator position
        sep_pos = -1
        for i in range(10, len(response) - 9):
            if response[i] == self.SEP:
                sep_pos = i
                break

        if sep_pos == -1:
            raise DatecsError("Separator not found")

        # Extract data
        data_bytes = response[10:sep_pos]
        data_str = data_bytes.decode('cp1251') if data_bytes else ""

        # Extract status bytes
        status_bytes = response[sep_pos + 1:sep_pos + 9]
        status = FiscalDeviceStatus(status_bytes)

        # Parse data fields
        data_fields = data_str.split('\t') if data_str else []

        # First field is typically error code
        error_code = 0
        if data_fields:
            try:
                error_code = int(data_fields[0])
            except (ValueError, IndexError):
                error_code = 0

        return DatecsResponse(
            error_code=error_code,
            data=data_fields[1:] if len(data_fields) > 1 else [],
            status=status,
            raw_message=response
        )

    def _send_receive(self, message: bytes, retries: int = 3) -> bytes:
        """
        Send message and receive response with error handling

        Args:
            message: Message to send
            retries: Number of retry attempts

        Returns:
            Response bytes
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            raise DatecsError("Serial connection not open")

        for attempt in range(retries + 1):
            try:
                # Clear input buffer
                self.serial_conn.reset_input_buffer()

                # Send message
                self.serial_conn.write(message)
                self.serial_conn.flush()

                # Read response
                response = b''
                start_time = time.time()

                while True:
                    # Check for timeout
                    if time.time() - start_time > self.timeout:
                        if attempt == retries:
                            raise DatecsTimeoutError("Response timeout")
                        break

                    # Read available data
                    if self.serial_conn.in_waiting:
                        chunk = self.serial_conn.read(self.serial_conn.in_waiting)
                        response += chunk

                        # Check for complete message
                        if response and response[-1] == self.EOT:
                            return response

                        # Check for single byte responses
                        if len(response) == 1:
                            if response[0] == self.NAK:
                                self.logger.warning("Received NAK, retrying...")
                                break
                            elif response[0] == self.SYN:
                                # Device needs more time
                                start_time = time.time()  # Reset timeout
                                response = b''  # Clear SYN
                                continue

                    time.sleep(0.001)  # Small delay to prevent CPU spinning

                # If we get here, either timeout or NAK occurred
                if attempt < retries:
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.1)

            except serial.SerialException as e:
                if attempt == retries:
                    raise DatecsError(f"Serial communication error: {e}")
                time.sleep(0.1)

        raise DatecsError("Max retries exceeded")

    def send_command(self, command: int, data: str = "") -> DatecsResponse:
        """
        Send command to device and return parsed response

        Args:
            command: Command code
            data: Command parameters separated by tabs

        Returns:
            Parsed response
        """
        # Build and send message
        message = self._build_message(command, data)

        self.logger.debug(f"Sending command {command:02X}: {data}")

        response_bytes = self._send_receive(message)
        response = self._parse_response(response_bytes)

        # Increment sequence number for next command
        self.sequence += 1
        if self.sequence > 0xFF:
            self.sequence = 0x20

        # Check for errors
        if response.error_code != 0:
            self.logger.warning(f"Command {command:02X} returned error: {response.error_code}")

        return response


class DatecsFiscalPrinter(DatecsProtocol):
    """
    High-level interface for Datecs fiscal printers

    This class provides convenient methods for common fiscal operations
    """

    def get_status(self) -> FiscalDeviceStatus:
        """Get current device status"""
        response = self.send_command(0x4A)  # Command 74 - Reading Status
        return response.status

    def get_device_info(self) -> Dict[str, str]:
        """Get device information"""
        response = self.send_command(0x7B, "1")  # Command 123 - Device Info

        if response.error_code == 0 and len(response.data) >= 7:
            return {
                'serial_number': response.data[0],
                'fiscal_number': response.data[1],
                'header_line1': response.data[2],
                'header_line2': response.data[3],
                'tax_number': response.data[4],
                'header_line3': response.data[5],
                'header_line4': response.data[6]
            }
        return {}

    def open_fiscal_receipt(self, operator_code: int = 1, operator_password: str = "1",
                            till_number: int = 1, invoice: bool = False) -> bool:
        """
        Open fiscal receipt

        Args:
            operator_code: Operator number (1-30)
            operator_password: Operator password
            till_number: Till number
            invoice: True for invoice receipt

        Returns:
            True if successful
        """
        invoice_flag = "I" if invoice else ""
        data = f"{operator_code}\t{operator_password}\t{till_number}\t{invoice_flag}"

        response = self.send_command(0x30, data)  # Command 48
        return response.error_code == 0

    def register_sale(self, plu_name: str, tax_group: str, price: float,
                      quantity: float = 1.0, department: int = 0) -> bool:
        """
        Register sale item

        Args:
            plu_name: Product name
            tax_group: Tax group (A-H)
            price: Unit price
            quantity: Quantity
            department: Department number

        Returns:
            True if successful
        """
        # Convert tax group letter to number
        tax_groups = {'A': 1, 'B': 2, 'C': 3, 'D': 4,
                      'E': 5, 'F': 6, 'G': 7, 'H': 8}
        tax_code = tax_groups.get(tax_group.upper(), 1)

        data = f"{plu_name}\t{tax_code}\t{price:.2f}\t{quantity:.3f}\t0\t\t{department}"

        response = self.send_command(0x31, data)  # Command 49
        return response.error_code == 0

    def subtotal(self, print_subtotal: bool = True) -> Optional[float]:
        """
        Print subtotal

        Args:
            print_subtotal: Whether to print subtotal

        Returns:
            Subtotal amount if successful
        """
        print_flag = "1" if print_subtotal else "0"
        response = self.send_command(0x33, print_flag)  # Command 51

        if response.error_code == 0 and len(response.data) >= 2:
            try:
                return float(response.data[1])
            except (ValueError, IndexError):
                pass
        return None

    def payment(self, payment_type: int = 0, amount: float = 0.0) -> bool:
        """
        Process payment

        Args:
            payment_type: Payment type (0=cash, 1=credit card, etc.)
            amount: Payment amount (0 for exact amount)

        Returns:
            True if successful
        """
        amount_str = f"{amount:.2f}" if amount > 0 else ""
        data = f"{payment_type}\t{amount_str}"

        response = self.send_command(0x35, data)  # Command 53
        return response.error_code == 0

    def close_fiscal_receipt(self) -> bool:
        """Close fiscal receipt"""
        response = self.send_command(0x38)  # Command 56
        return response.error_code == 0

    def cancel_fiscal_receipt(self) -> bool:
        """Cancel current fiscal receipt"""
        response = self.send_command(0x3C)  # Command 60
        return response.error_code == 0

    def print_z_report(self) -> bool:
        """Print daily Z report"""
        response = self.send_command(0x45, "Z")  # Command 69
        return response.error_code == 0

    def print_x_report(self) -> bool:
        """Print daily X report"""
        response = self.send_command(0x45, "X")  # Command 69
        return response.error_code == 0

    def set_date_time(self, datetime_str: str) -> bool:
        """
        Set device date and time

        Args:
            datetime_str: Date/time in format "DD-MM-YY hh:mm:ss"

        Returns:
            True if successful
        """
        response = self.send_command(0x3D, datetime_str)  # Command 61
        return response.error_code == 0

    def get_date_time(self) -> Optional[str]:
        """Get device date and time"""
        response = self.send_command(0x3E)  # Command 62

        if response.error_code == 0 and response.data:
            return response.data[0]
        return None


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    try:
        # Initialize printer (adjust port as needed)
        with DatecsFiscalPrinter("/dev/ttyUSB0", baudrate=115200) as printer:

            # Get device status
            status = printer.get_status()
            print(f"Device fiscalized: {status.device_fiscalized}")
            print(f"Paper end: {status.end_of_paper}")
            print(f"Cover open: {status.cover_open}")

            # Get device info
            info = printer.get_device_info()
            print(f"Serial: {info.get('serial_number', 'N/A')}")
            print(f"Fiscal: {info.get('fiscal_number', 'N/A')}")

            # Example fiscal receipt
            if printer.open_fiscal_receipt(operator_code=1, operator_password="1"):
                printer.register_sale("Хляб", "B", 2.50, 1.0)
                printer.register_sale("Мляко", "B", 3.20, 2.0)

                subtotal = printer.subtotal()
                if subtotal:
                    print(f"Subtotal: {subtotal:.2f}")

                printer.payment(payment_type=0)  # Cash payment
                printer.close_fiscal_receipt()

                print("Receipt printed successfully")

    except DatecsError as e:
        print(f"Datecs error: {e}")
    except Exception as e:
        print(f"Error: {e}")

