# -*- coding: utf-8 -*-
"""
Odoo IoT Driver for Datecs Fiscal Printers
Compatible with Datecs Communication Protocol v2.11
"""

import serial
import time
import logging
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

try:
    from odoo.addons.hw_drivers.controllers.driver import Driver, event_manager
    from odoo.addons.hw_drivers.tools import helpers
    from odoo.addons.hw_drivers.event_manager import event_manager
except ImportError:
    # Fallback for testing outside Odoo environment
    class Driver:
        def __init__(self, device):
            self.device = device

        def supported(self, device):
            return False


    class event_manager:
        @staticmethod
        def device_changed(device):
            pass

_logger = logging.getLogger(__name__)


class DatecsError(Exception):
    """Custom exception for Datecs communication errors"""
    pass


class DatecsTimeoutError(DatecsError):
    """Timeout error for Datecs communication"""
    pass


class FiscalDeviceStatus:
    """Status byte interpretation for Datecs fiscal devices"""

    def __init__(self, status_bytes: bytes):
        if len(status_bytes) != 8:
            raise ValueError("Status bytes must be exactly 8 bytes long")

        self.status_bytes = status_bytes
        self.bits = []

        # Convert each byte to 8 bits (LSB first)
        for byte in status_bytes:
            bits = []
            for i in range(8):
                bits.append((byte >> i) & 1)
            self.bits.extend(bits)

    def to_dict(self) -> Dict[str, bool]:
        """Convert status to dictionary for JSON serialization"""
        return {
            'cover_open': self.cover_open,
            'general_error': self.general_error,
            'printer_failure': self.printer_failure,
            'rtc_not_synchronized': self.rtc_not_synchronized,
            'invalid_command': self.invalid_command,
            'syntax_error': self.syntax_error,
            'non_fiscal_receipt_open': self.non_fiscal_receipt_open,
            'ej_nearly_full': self.ej_nearly_full,
            'fiscal_receipt_open': self.fiscal_receipt_open,
            'ej_full': self.ej_full,
            'near_paper_end': self.near_paper_end,
            'end_of_paper': self.end_of_paper,
            'fiscal_memory_damaged': self.fiscal_memory_damaged,
            'fiscal_memory_full': self.fiscal_memory_full,
            'device_fiscalized': self.device_fiscalized,
        }

    @property
    def cover_open(self) -> bool:
        return bool(self.bits[6])  # Byte 0, Bit 6

    @property
    def general_error(self) -> bool:
        return bool(self.bits[5])  # Byte 0, Bit 5

    @property
    def printer_failure(self) -> bool:
        return bool(self.bits[4])  # Byte 0, Bit 4

    @property
    def rtc_not_synchronized(self) -> bool:
        return bool(self.bits[2])  # Byte 0, Bit 2

    @property
    def invalid_command(self) -> bool:
        return bool(self.bits[1])  # Byte 0, Bit 1

    @property
    def syntax_error(self) -> bool:
        return bool(self.bits[0])  # Byte 0, Bit 0

    @property
    def non_fiscal_receipt_open(self) -> bool:
        return bool(self.bits[21])  # Byte 2, Bit 5

    @property
    def ej_nearly_full(self) -> bool:
        return bool(self.bits[20])  # Byte 2, Bit 4

    @property
    def fiscal_receipt_open(self) -> bool:
        return bool(self.bits[19])  # Byte 2, Bit 3

    @property
    def ej_full(self) -> bool:
        return bool(self.bits[18])  # Byte 2, Bit 2

    @property
    def near_paper_end(self) -> bool:
        return bool(self.bits[17])  # Byte 2, Bit 1

    @property
    def end_of_paper(self) -> bool:
        return bool(self.bits[16])  # Byte 2, Bit 0

    @property
    def fiscal_memory_damaged(self) -> bool:
        return bool(self.bits[38])  # Byte 4, Bit 6

    @property
    def fiscal_memory_full(self) -> bool:
        return bool(self.bits[36])  # Byte 4, Bit 4

    @property
    def device_fiscalized(self) -> bool:
        return bool(self.bits[43])  # Byte 5, Bit 3


class DatecsProtocol:
    """Low-level Datecs protocol implementation"""

    # Protocol constants
    PRE = 0x01
    PST = 0x05
    SEP = 0x04
    EOT = 0x03
    NAK = 0x15
    SYN = 0x16

    DEFAULT_TIMEOUT = 2.0

    def __init__(self, device_path: str, baudrate: int = 115200):
        self.device_path = device_path
        self.baudrate = baudrate
        self.sequence = 0x20
        self.serial_conn: Optional[serial.Serial] = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Establish connection to device"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                return True

            self.serial_conn = serial.Serial(
                port=self.device_path,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.DEFAULT_TIMEOUT
            )

            _logger.info(f"Connected to Datecs device at {self.device_path}")
            return True

        except serial.SerialException as e:
            _logger.error(f"Failed to connect to {self.device_path}: {e}")
            return False

    def disconnect(self):
        """Close connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            _logger.info("Disconnected from Datecs device")

    def _ascii_hex_encode(self, value: int, length: int) -> bytes:
        """Convert integer to ASCII-hex format"""
        hex_str = f"{value:0{length}X}"
        return bytes([ord(c) + 0x30 for c in hex_str])

    def _ascii_hex_decode(self, data: bytes) -> int:
        """Decode ASCII-hex format to integer"""
        hex_str = ''.join([chr(b - 0x30) for b in data])
        return int(hex_str, 16)

    def _calculate_bcc(self, data: bytes) -> int:
        """Calculate block check character"""
        return sum(data) & 0xFFFF

    def _build_message(self, command: int, data: str = "") -> bytes:
        """Build complete message frame"""
        data_bytes = data.encode('cp1251') if data else b''

        message_parts = [
            self._ascii_hex_encode(len(data_bytes) + 10 + 0x20, 4),
            bytes([self.sequence]),
            self._ascii_hex_encode(command, 4),
            data_bytes,
            bytes([self.PST])
        ]

        message_for_bcc = b''.join(message_parts)
        bcc = self._calculate_bcc(message_for_bcc)
        message_parts.append(self._ascii_hex_encode(bcc, 4))

        return bytes([self.PRE]) + b''.join(message_parts) + bytes([self.EOT])

    def _parse_response(self, response: bytes) -> Dict[str, Any]:
        """Parse device response"""
        if len(response) < 15:
            raise DatecsError("Response too short")

        if response[0] != self.PRE or response[-1] != self.EOT:
            raise DatecsError("Invalid frame format")

        # Find separator
        sep_pos = -1
        for i in range(10, len(response) - 9):
            if response[i] == self.SEP:
                sep_pos = i
                break

        if sep_pos == -1:
            raise DatecsError("Separator not found")

        # Extract data and status
        data_bytes = response[10:sep_pos]
        status_bytes = response[sep_pos + 1:sep_pos + 9]

        data_str = data_bytes.decode('cp1251', errors='ignore') if data_bytes else ""
        data_fields = data_str.split('\t') if data_str else []

        # Parse error code
        error_code = 0
        if data_fields:
            try:
                error_code = int(data_fields[0])
            except (ValueError, IndexError):
                pass

        return {
            'error_code': error_code,
            'data': data_fields[1:] if len(data_fields) > 1 else [],
            'status': FiscalDeviceStatus(status_bytes),
            'raw_response': response.hex()
        }

    def send_command(self, command: int, data: str = "") -> Dict[str, Any]:
        """Send command and return response"""
        with self._lock:
            if not self.connect():
                raise DatecsError("Cannot connect to device")

            message = self._build_message(command, data)

            try:
                # Clear buffers
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()

                # Send message
                self.serial_conn.write(message)
                self.serial_conn.flush()

                # Read response
                response = self._read_response()
                result = self._parse_response(response)

                # Update sequence
                self.sequence += 1
                if self.sequence > 0xFF:
                    self.sequence = 0x20

                return result

            except serial.SerialException as e:
                _logger.error(f"Serial communication error: {e}")
                raise DatecsError(f"Communication error: {e}")

    def _read_response(self, timeout: float = 3.0) -> bytes:
        """Read complete response from device"""
        response = b''
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.serial_conn.in_waiting:
                chunk = self.serial_conn.read(self.serial_conn.in_waiting)
                response += chunk

                # Check for single byte responses
                if len(response) == 1:
                    if response[0] == self.NAK:
                        raise DatecsError("Device sent NAK")
                    elif response[0] == self.SYN:
                        response = b''  # Clear SYN and continue
                        start_time = time.time()  # Reset timeout
                        continue

                # Check for complete message
                if response and response[-1] == self.EOT:
                    return response

            time.sleep(0.01)

        raise DatecsTimeoutError("Response timeout")


class DatecsDriver(Driver):
    """Odoo IoT Driver for Datecs Fiscal Printers"""

    connection_type = 'serial'

    def __init__(self, device):
        super(DatecsDriver, self).__init__(device)
        self.device = device
        self.protocol = None
        self._status = {}
        self._info = {}

        # Initialize protocol if device path is available
        if hasattr(device, 'device_path') and device.device_path:
            self.protocol = DatecsProtocol(device.device_path)
            self._initialize_device()

    @classmethod
    def supported(cls, device):
        """Check if device is supported Datecs fiscal printer"""
        try:
            # Check if it's a serial device
            if not hasattr(device, 'device_path'):
                return False

            # Try to identify Datecs device
            protocol = DatecsProtocol(device.device_path)
            if protocol.connect():
                try:
                    # Try to get device info (Command 123)
                    response = protocol.send_command(0x7B, "1")
                    protocol.disconnect()

                    # If we get a valid response, it's likely a Datecs device
                    return response.get('error_code', -1) >= 0

                except Exception:
                    protocol.disconnect()
                    return False

            return False

        except Exception as e:
            _logger.debug(f"Device check failed: {e}")
            return False

    def _initialize_device(self):
        """Initialize device and get basic info"""
        try:
            if not self.protocol:
                return

            # Get device info
            self._update_device_info()

            # Get initial status
            self._update_status()

            _logger.info(f"Datecs device initialized: {self._info}")

        except Exception as e:
            _logger.error(f"Failed to initialize Datecs device: {e}")

    def _update_device_info(self):
        """Update device information"""
        try:
            # Get device diagnostic info (Command 123, option 1)
            response = self.protocol.send_command(0x7B, "1")

            if response.get('error_code') == 0 and response.get('data'):
                data = response['data']
                self._info = {
                    'model': 'Datecs Fiscal Printer',
                    'serial_number': data[0] if len(data) > 0 else 'Unknown',
                    'fiscal_number': data[1] if len(data) > 1 else 'Unknown',
                    'header_line1': data[2] if len(data) > 2 else '',
                    'header_line2': data[3] if len(data) > 3 else '',
                    'tax_number': data[4] if len(data) > 4 else '',
                    'last_updated': datetime.now().isoformat()
                }

        except Exception as e:
            _logger.error(f"Failed to get device info: {e}")
            self._info = {'model': 'Datecs Fiscal Printer', 'error': str(e)}

    def _update_status(self):
        """Update device status"""
        try:
            # Get device status (Command 74)
            response = self.protocol.send_command(0x4A)

            if 'status' in response:
                status_dict = response['status'].to_dict()
                self._status = {
                    **status_dict,
                    'last_updated': datetime.now().isoformat(),
                    'connected': True,
                    'error_code': response.get('error_code', 0)
                }
            else:
                self._status = {
                    'connected': False,
                    'error': 'Failed to get status',
                    'last_updated': datetime.now().isoformat()
                }

        except Exception as e:
            _logger.error(f"Failed to get device status: {e}")
            self._status = {
                'connected': False,
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }

    def action_print_fiscal_receipt(self, receipt_data):
        """Print fiscal receipt"""
        try:
            if not self.protocol:
                return {'success': False, 'error': 'Device not initialized'}

            # Extract receipt data
            operator = receipt_data.get('operator', {})
            operator_code = operator.get('code', 1)
            operator_password = operator.get('password', '1')
            till_number = receipt_data.get('till_number', 1)

            lines = receipt_data.get('lines', [])
            payments = receipt_data.get('payments', [])

            # Open fiscal receipt
            invoice_flag = "I" if receipt_data.get('is_invoice', False) else ""
            open_data = f"{operator_code}\t{operator_password}\t{till_number}\t{invoice_flag}"

            response = self.protocol.send_command(0x30, open_data)  # Command 48
            if response.get('error_code') != 0:
                return {'success': False, 'error': f'Failed to open receipt: {response.get("error_code")}'}

            # Register items
            for line in lines:
                tax_groups = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8}
                tax_code = tax_groups.get(line.get('tax_group', 'B').upper(), 2)

                line_data = (f"{line.get('name', '')}\t{tax_code}\t{line.get('price', 0):.2f}\t"
                             f"{line.get('quantity', 1):.3f}\t0\t\t{line.get('department', 0)}")

                response = self.protocol.send_command(0x31, line_data)  # Command 49
                if response.get('error_code') != 0:
                    # Try to cancel receipt on error
                    self.protocol.send_command(0x3C)  # Command 60 - Cancel
                    return {'success': False, 'error': f'Failed to register item: {response.get("error_code")}'}

            # Process payments
            for payment in payments:
                payment_data = f"{payment.get('type', 0)}\t{payment.get('amount', 0):.2f}"
                response = self.protocol.send_command(0x35, payment_data)  # Command 53
                if response.get('error_code') != 0:
                    self.protocol.send_command(0x3C)  # Cancel receipt
                    return {'success': False, 'error': f'Failed to process payment: {response.get("error_code")}'}

            # Close receipt
            response = self.protocol.send_command(0x38)  # Command 56
            if response.get('error_code') != 0:
                return {'success': False, 'error': f'Failed to close receipt: {response.get("error_code")}'}

            # Update status after printing
            self._update_status()

            return {'success': True, 'receipt_number': response.get('data', [None])[0]}

        except Exception as e:
            _logger.error(f"Error printing fiscal receipt: {e}")
            try:
                # Try to cancel any open receipt
                self.protocol.send_command(0x3C)
            except:
                pass
            return {'success': False, 'error': str(e)}

    def action_print_z_report(self):
        """Print daily Z report"""
        try:
            if not self.protocol:
                return {'success': False, 'error': 'Device not initialized'}

            response = self.protocol.send_command(0x45, "Z")  # Command 69
            self._update_status()

            if response.get('error_code') == 0:
                return {'success': True, 'report_number': response.get('data', [None])[0]}
            else:
                return {'success': False, 'error': f'Z report failed: {response.get("error_code")}'}

        except Exception as e:
            _logger.error(f"Error printing Z report: {e}")
            return {'success': False, 'error': str(e)}

    def action_print_x_report(self):
        """Print X report"""
        try:
            if not self.protocol:
                return {'success': False, 'error': 'Device not initialized'}

            response = self.protocol.send_command(0x45, "X")  # Command 69
            self._update_status()

            if response.get('error_code') == 0:
                return {'success': True}
            else:
                return {'success': False, 'error': f'X report failed: {response.get("error_code")}'}

        except Exception as e:
            _logger.error(f"Error printing X report: {e}")
            return {'success': False, 'error': str(e)}

    def action_get_status(self):
        """Get current device status"""
        self._update_status()
        return {
            'success': True,
            'status': self._status,
            'info': self._info
        }

    def action_set_datetime(self, datetime_str):
        """Set device date and time"""
        try:
            if not self.protocol:
                return {'success': False, 'error': 'Device not initialized'}

            response = self.protocol.send_command(0x3D, datetime_str)  # Command 61

            if response.get('error_code') == 0:
                return {'success': True}
            else:
                return {'success': False, 'error': f'Set datetime failed: {response.get("error_code")}'}

        except Exception as e:
            _logger.error(f"Error setting datetime: {e}")
            return {'success': False, 'error': str(e)}

    def action_cancel_receipt(self):
        """Cancel current fiscal receipt"""
        try:
            if not self.protocol:
                return {'success': False, 'error': 'Device not initialized'}

            response = self.protocol.send_command(0x3C)  # Command 60
            self._update_status()

            if response.get('error_code') == 0:
                return {'success': True}
            else:
                return {'success': False, 'error': f'Cancel receipt failed: {response.get("error_code")}'}

        except Exception as e:
            _logger.error(f"Error canceling receipt: {e}")
            return {'success': False, 'error': str(e)}

    def action_get_last_receipt_info(self):
        """Get information about last receipt"""
        try:
            if not self.protocol:
                return {'success': False, 'error': 'Device not initialized'}

            # Command 74 with option '0' - current receipt status
            response = self.protocol.send_command(0x4A, "0")

            if response.get('error_code') == 0 and response.get('data'):
                data = response['data']
                return {
                    'success': True,
                    'print_buffer_status': data[0] if len(data) > 0 else '0',
                    'receipt_status': data[1] if len(data) > 1 else '0',
                    'receipt_number': data[2] if len(data) > 2 else '0',
                    'qr_amount': data[3] if len(data) > 3 else '0.00',
                    'qr_number': data[4] if len(data) > 4 else '0',
                    'qr_datetime': data[5] if len(data) > 5 else ''
                }
            else:
                return {'success': False, 'error': f'Get receipt info failed: {response.get("error_code")}'}

        except Exception as e:
            _logger.error(f"Error getting receipt info: {e}")
            return {'success': False, 'error': str(e)}


# Register the driver with Odoo IoT system
try:
    # This will be called when the module is loaded in Odoo IoT
    drivers = [DatecsDriver]
except NameError:
    # Fallback for testing
    pass

# Example usage for testing
if __name__ == "__main__":
    # Test the driver outside Odoo environment
    import sys

    logging.basicConfig(level=logging.DEBUG)


    class TestDevice:
        def __init__(self, device_path):
            self.device_path = device_path


    if len(sys.argv) > 1:
        device_path = sys.argv[1]
    else:
        device_path = "/dev/ttyUSB0"  # Default device path

    device = TestDevice(device_path)
    driver = DatecsDriver(device)

    if DatecsDriver.supported(device):
        print("Device supported!")

        # Test status
        result = driver.action_get_status()
        print(f"Status: {json.dumps(result, indent=2)}")

        # Test fiscal receipt
        receipt_data = {
            'operator': {'code': 1, 'password': '1'},
            'till_number': 1,
            'lines': [
                {'name': 'Тест продукт', 'price': 10.50, 'quantity': 2, 'tax_group': 'B'}
            ],
            'payments': [
                {'type': 0, 'amount': 21.00}  # Cash payment
            ]
        }

        result = driver.action_print_fiscal_receipt(receipt_data)
        print(f"Receipt result: {json.dumps(result, indent=2)}")

    else:
        print("Device not supported or not found")
