import serial
import socket
import time
from typing import Union, Optional, Dict, List, Tuple
from enum import Enum
import logging


class ConnectionType(Enum):
    SERIAL = "serial"
    TCP = "tcp"


class VATClass(Enum):
    VAT_A = "А"
    VAT_B = "Б"
    VAT_C = "В"
    VAT_D = "Г"
    VAT_E = "Д"
    VAT_F = "Е"
    VAT_G = "Ж"
    VAT_H = "З"
    FORBIDDEN = "*"


class PaymentType(Enum):
    CASH = "0"
    PAYMENT_1 = "1"
    PAYMENT_2 = "2"
    PAYMENT_3 = "3"
    PAYMENT_4 = "4"
    PAYMENT_5 = "5"
    PAYMENT_6 = "6"
    PAYMENT_7 = "7"
    PAYMENT_8 = "8"
    PAYMENT_9 = "9"
    PAYMENT_10 = "10"
    CURRENCY = "11"


class FiscalPrinterError(Exception):
    """Custom exception for fiscal printer errors"""

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"Error {error_code}: {message}")


class FiscalPrinterDriver:
    """
    Driver for Bulgarian fiscal printers implementing the communication protocol
    """

    # Error codes mapping
    ERROR_CODES = {
        "30": "OK",
        "31": "Out of paper, printer failure",
        "32": "Registers overflow",
        "33": "Clock failure or incorrect date&time",
        "34": "Opened fiscal receipt",
        "35": "Payment residue account",
        "36": "Opened non-fiscal receipt",
        "37": "Registered payment but receipt is not closed",
        "38": "Fiscal memory failure",
        "39": "Incorrect password",
        "3a": "Missing external display",
        "3b": "24hours block – unprinted Z report",
        "3c": "Overheated printer thermal head",
        "3d": "Interrupt power supply in fiscal receipt",
        "3e": "Overflow EJ",
        "3f": "Insufficient conditions"
    }

    COMMAND_ERROR_CODES = {
        "30": "OK",
        "31": "Invalid command",
        "32": "Illegal command",
        "33": "Z daily report is not zero",
        "34": "Syntax error",
        "35": "Input registers overflow",
        "36": "Zero input registers",
        "37": "Unavailable transaction for correction",
        "38": "Insufficient amount on hand"
    }

    def __init__(self, connection_type: ConnectionType, **kwargs):
        """
        Initialize fiscal printer driver

        Args:
            connection_type: Type of connection (SERIAL or TCP)
            **kwargs: Connection parameters
                For SERIAL: port, baudrate (default 115200)
                For TCP: host, port (default 8000), password
        """
        self.connection_type = connection_type
        self.connection = None
        self.message_counter = 0x20  # Start from 0x20
        self.logger = logging.getLogger(__name__)

        if connection_type == ConnectionType.SERIAL:
            self.port = kwargs.get('port')
            self.baudrate = kwargs.get('baudrate', 115200)
            if not self.port:
                raise ValueError("Serial port must be specified")

        elif connection_type == ConnectionType.TCP:
            self.host = kwargs.get('host')
            self.port = kwargs.get('port', 8000)
            self.password = kwargs.get('password', '')
            if not self.host:
                raise ValueError("TCP host must be specified")

    def connect(self):
        """Establish connection to the fiscal printer"""
        try:
            if self.connection_type == ConnectionType.SERIAL:
                self.connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=8,
                    parity=serial.PARITY_NONE,
                    stopbits=1,
                    timeout=5
                )

            elif self.connection_type == ConnectionType.TCP:
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connection.connect((self.host, self.port))
                self.connection.settimeout(5)

                # Send password if provided
                if self.password:
                    password_data = self.password.encode() + b'\x0A'
                    self.connection.send(password_data)

            self.logger.info("Connected to fiscal printer")

        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            raise FiscalPrinterError("CONNECTION", f"Connection failed: {e}")

    def disconnect(self):
        """Close connection to the fiscal printer"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Disconnected from fiscal printer")

    def _calculate_checksum(self, data: bytes) -> bytes:
        """Calculate XOR checksum and convert to 2 ASCII bytes"""
        checksum = 0
        for byte in data:
            checksum ^= byte

        # Convert to 2 bytes by adding 0x30
        high_byte = ((checksum >> 4) & 0x0F) + 0x30
        low_byte = (checksum & 0x0F) + 0x30

        return bytes([high_byte, low_byte])

    def _build_message(self, command: int, data: str = "") -> bytes:
        """Build complete message according to protocol"""
        # Convert data to bytes
        data_bytes = data.encode('cp1251')

        # Calculate length (LEN + NBL + CMD + DATA)
        length = 3 + len(data_bytes)
        len_byte = length + 0x20

        # Get message number
        nbl_byte = self.message_counter
        self.message_counter += 1
        if self.message_counter > 0x9F:
            self.message_counter = 0x20

        # Build message without STX, CS, ETX
        msg_core = bytes([len_byte, nbl_byte, command]) + data_bytes

        # Calculate checksum
        checksum = self._calculate_checksum(msg_core)

        # Build complete message
        message = bytes([0x02]) + msg_core + checksum + bytes([0x0A])

        return message

    def _send_message(self, message: bytes) -> bytes:
        """Send message and receive response"""
        if not self.connection:
            raise FiscalPrinterError("CONNECTION", "Not connected to printer")

        try:
            if self.connection_type == ConnectionType.SERIAL:
                self.connection.write(message)
                response = self.connection.read(1024)

            elif self.connection_type == ConnectionType.TCP:
                self.connection.send(message)
                response = self.connection.recv(1024)

            return response

        except Exception as e:
            self.logger.error(f"Communication error: {e}")
            raise FiscalPrinterError("COMMUNICATION", f"Communication failed: {e}")

    def _parse_response(self, response: bytes) -> Tuple[str, Optional[str]]:
        """Parse response from fiscal printer"""
        if len(response) < 7:
            raise FiscalPrinterError("PROTOCOL", "Invalid response length")

        if response[0] == 0x06:  # ACK response
            nbl = response[1]
            status1 = chr(response[2])
            status2 = chr(response[3])

            status_code = status1 + status2

            if status_code != "30":
                error_msg = self.ERROR_CODES.get(status1 + "0", "Unknown error")
                cmd_error_msg = self.COMMAND_ERROR_CODES.get(status2 + "0", "Unknown command error")
                raise FiscalPrinterError(status_code, f"{error_msg} / {cmd_error_msg}")

            return "ACK", None

        elif response[0] == 0x15:  # NACK
            raise FiscalPrinterError("NACK", "Negative acknowledgment")

        elif response[0] == 0x0E:  # RETRY
            raise FiscalPrinterError("RETRY", "Device busy")

        elif response[0] == 0x02:  # Message response
            # Parse message response
            length = response[1] - 0x20
            nbl = response[2]
            cmd = response[3]

            if length > 4:
                data = response[4:4 + length - 3].decode('cp1251')
                return "DATA", data
            else:
                return "DATA", ""

        else:
            raise FiscalPrinterError("PROTOCOL", "Unknown response type")

    def _send_command(self, command: int, data: str = "") -> Optional[str]:
        """Send command and handle response with retries"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                message = self._build_message(command, data)
                self.logger.debug(f"Sending command 0x{command:02X}: {data}")

                response = self._send_message(message)
                response_type, response_data = self._parse_response(response)

                if response_type == "ACK":
                    return None
                elif response_type == "DATA":
                    return response_data

            except FiscalPrinterError as e:
                if e.error_code == "RETRY" and attempt < max_retries - 1:
                    time.sleep(0.1)
                    continue
                else:
                    raise

    def check_status(self) -> bytes:
        """Quick status check using unpacked commands"""
        if not self.connection:
            raise FiscalPrinterError("CONNECTION", "Not connected to printer")

        try:
            if self.connection_type == ConnectionType.SERIAL:
                self.connection.write(bytes([0x04]))
                response = self.connection.read(1)

            elif self.connection_type == ConnectionType.TCP:
                self.connection.send(bytes([0x04]))
                response = self.connection.recv(1)

            return response

        except Exception as e:
            raise FiscalPrinterError("STATUS", f"Status check failed: {e}")

    def get_status(self) -> Dict:
        """Get detailed status information (Command 20h)"""
        response = self._send_command(0x20)
        if response and len(response) >= 14:
            # Parse 7-byte status information
            status = {}
            status['fm_read_only'] = bool(int(response[0]) & 0x01)
            status['power_down_in_receipt'] = bool(int(response[0]) & 0x02)
            status['printer_not_ready_overheat'] = bool(int(response[0]) & 0x04)
            # Add more status parsing as needed
            return status
        return {}

    def get_version(self) -> Dict:
        """Get device version information (Command 21h)"""
        response = self._send_command(0x21)
        if response:
            parts = response.split(';')
            if len(parts) >= 5:
                return {
                    'device_type': parts[0],
                    'certificate_num': parts[1],
                    'certificate_date': parts[2],
                    'model': parts[3],
                    'version': parts[4]
                }
        return {}

    def open_fiscal_receipt(self, operator_num: str, operator_pass: str,
                            receipt_format: str = "1", print_vat: str = "1",
                            print_type: str = "0", unique_receipt_num: str = "") -> None:
        """
        Open fiscal receipt (Command 30h)

        Args:
            operator_num: Operator number (1-20)
            operator_pass: 6-digit operator password
            receipt_format: '1' for detailed, '0' for brief
            print_vat: '1' to print VAT, '0' to not print
            print_type: '0' step-by-step, '2' postponed, '4' buffered
            unique_receipt_num: Optional unique receipt number
        """
        data = f"{operator_num};{operator_pass};{receipt_format};{print_vat};{print_type}"

        if unique_receipt_num:
            data += f"${unique_receipt_num}"

        self._send_command(0x30, data)
        self.logger.info("Fiscal receipt opened")

    def sell_item(self, name: str, vat_class: VATClass, price: float,
                  quantity: Optional[float] = None, discount_percent: Optional[float] = None,
                  discount_value: Optional[float] = None) -> None:
        """
        Register item sale (Command 31h)

        Args:
            name: Item name (up to 36 characters)
            vat_class: VAT class enum
            price: Item price
            quantity: Optional quantity (default 1.000)
            discount_percent: Optional discount percentage
            discount_value: Optional discount value
        """
        # Limit name to 36 characters
        name = name[:36]

        data = f"{name};{vat_class.value};{price:.2f}"

        if quantity is not None:
            data += f"*{quantity:.3f}"

        if discount_percent is not None:
            data += f",{discount_percent:.2f}"

        if discount_value is not None:
            data += f":{discount_value:.2f}"

        self._send_command(0x31, data)
        self.logger.debug(f"Item sold: {name}, Price: {price:.2f}")

    def subtotal(self, print_subtotal: bool = True, display_subtotal: bool = True,
                 discount_value: Optional[float] = None, discount_percent: Optional[float] = None) -> float:
        """
        Calculate subtotal (Command 33h)

        Args:
            print_subtotal: Whether to print subtotal
            display_subtotal: Whether to display subtotal
            discount_value: Optional discount value
            discount_percent: Optional discount percentage

        Returns:
            Subtotal amount
        """
        data = f"{'1' if print_subtotal else '0'};{'1' if display_subtotal else '0'}"

        if discount_value is not None:
            data += f":{discount_value:.2f}"

        if discount_percent is not None:
            data += f",{discount_percent:.2f}"

        response = self._send_command(0x33, data)

        if response:
            try:
                return float(response)
            except ValueError:
                pass

        return 0.0

    def payment(self, payment_type: PaymentType, amount: float,
                change_type: str = "0", without_change: bool = False) -> None:
        """
        Register payment (Command 35h)

        Args:
            payment_type: Type of payment
            amount: Payment amount
            change_type: '0' change in cash, '1' same as payment, '2' change in currency
            without_change: True if no change should be given
        """
        change_option = "1" if without_change else "0"
        data = f"{payment_type.value};{change_option};{amount:.2f}"

        if not without_change:
            data += f";{change_type}"

        self._send_command(0x35, data)
        self.logger.debug(f"Payment registered: {amount:.2f}")

    def cash_payment_and_close(self) -> None:
        """Pay exact amount in cash and close receipt (Command 36h)"""
        self._send_command(0x36)
        self.logger.info("Cash payment and receipt closed")

    def close_receipt(self) -> None:
        """Close fiscal receipt (Command 38h)"""
        self._send_command(0x38)
        self.logger.info("Fiscal receipt closed")

    def cancel_receipt(self) -> None:
        """Cancel fiscal receipt (Command 39h)"""
        self._send_command(0x39)
        self.logger.info("Fiscal receipt cancelled")

    def print_daily_report(self, with_zeroing: bool = False) -> None:
        """
        Print daily report (Command 7Ch)

        Args:
            with_zeroing: True for Z report (with zeroing), False for X report
        """
        option = "Z" if with_zeroing else "X"
        self._send_command(0x7C, option)
        self.logger.info(f"Daily report printed ({'Z' if with_zeroing else 'X'})")

    def print_text(self, text: str) -> None:
        """
        Print free text (Command 37h)

        Args:
            text: Text to print (will be surrounded by # symbols)
        """
        self._send_command(0x37, text)

    def open_drawer(self) -> None:
        """Open cash drawer (Command 2Ah)"""
        self._send_command(0x2A)
        self.logger.debug("Cash drawer opened")

    def cut_paper(self) -> None:
        """Cut paper - FP only (Command 29h)"""
        self._send_command(0x29)
        self.logger.debug("Paper cut")

    def feed_paper(self) -> None:
        """Feed one line of paper (Command 2Bh)"""
        self._send_command(0x2B)


# Example usage and test functions
class FiscalPrinterTest:
    """Test class for fiscal printer operations"""

    def __init__(self, driver: FiscalPrinterDriver):
        self.driver = driver

    def test_connection(self):
        """Test basic connection and status"""
        print("Testing connection...")
        try:
            status = self.driver.check_status()
            print(f"Status response: {status.hex() if status else 'No response'}")

            version = self.driver.get_version()
            print(f"Version info: {version}")

            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def test_simple_receipt(self):
        """Test simple receipt with one item"""
        print("Testing simple receipt...")
        try:
            # Open receipt
            self.driver.open_fiscal_receipt("1", "000000")

            # Add item
            self.driver.sell_item("Test Item", VATClass.VAT_A, 10.00, quantity=1.0)

            # Calculate subtotal
            subtotal = self.driver.subtotal()
            print(f"Subtotal: {subtotal:.2f}")

            # Pay and close
            self.driver.cash_payment_and_close()

            print("Simple receipt test completed successfully")
            return True

        except Exception as e:
            print(f"Receipt test failed: {e}")
            try:
                self.driver.cancel_receipt()
            except:
                pass
            return False


def main():
    """Example usage"""
    # Example for serial connection
    try:
        # Initialize driver
        driver = FiscalPrinterDriver(
            ConnectionType.SERIAL,
            port="COM1",  # Adjust port as needed
            baudrate=115200
        )

        # Or for TCP connection:
        # driver = FiscalPrinterDriver(
        #     ConnectionType.TCP,
        #     host="192.168.1.100",
        #     port=8000,
        #     password="1234"
        # )

        # Connect
        driver.connect()

        # Run tests
        test = FiscalPrinterTest(driver)

        if test.test_connection():
            test.test_simple_receipt()

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if 'driver' in locals():
            driver.disconnect()


if __name__ == "__main__":
    main()
