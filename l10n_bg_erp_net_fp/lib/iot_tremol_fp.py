#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Union
from enum import Enum
import logging

try:
    import serial
except ImportError:
    serial = None

try:
    import socket
except ImportError:
    socket = None

# Odoo IoT specific imports
try:
    from odoo.addons.hw_drivers.driver import Driver
    from odoo.addons.hw_drivers.event_manager import event_manager

    ODOO_IOT = True
except ImportError:
    # Fallback for standalone usage
    ODOO_IOT = False


    class Driver:
        def __init__(self, device):
            self.device = device


class VATClass(Enum):
    """VAT class definitions"""
    VAT_A = "А"  # Usually 20%
    VAT_B = "Б"  # Usually 9%
    VAT_C = "В"  # Usually 0%
    VAT_D = "Г"
    VAT_E = "Д"
    VAT_F = "Е"
    VAT_G = "Ж"
    VAT_H = "З"
    FORBIDDEN = "*"


class PaymentType(Enum):
    """Payment type definitions"""
    CASH = "0"
    CARD = "7"
    BANK = "8"
    CURRENCY = "11"


class FiscalPrinterError(Exception):
    """Custom exception for fiscal printer errors"""

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"Error {error_code}: {message}")


class BulgarianFiscalDriver(Driver if ODOO_IOT else object):
    """
    Odoo IoT driver for Bulgarian fiscal printers
    Optimized for resource-constrained devices
    """

    connection_type = 'fiscal_printer'

    # Compact error code mapping for memory efficiency
    ERROR_CODES = {
        "31": "No paper",
        "32": "Overflow",
        "33": "Clock error",
        "34": "Receipt open",
        "35": "Payment error",
        "36": "Non-fiscal open",
        "37": "Payment not closed",
        "38": "FM failure",
        "39": "Wrong password",
        "3b": "Z report needed",
        "3c": "Overheated",
        "3d": "Power interrupt",
        "3e": "EJ overflow"
    }

    def __init__(self, device=None):
        if ODOO_IOT:
            super().__init__(device)

        self.device_name = getattr(device, 'name', 'fiscal_printer') if device else 'fiscal_printer'
        self.connection = None
        self.message_counter = 0x20
        self.lock = threading.Lock()
        self.last_error = None

        # IoT optimized configuration
        self.config = {
            'timeout': 3,
            'max_retries': 2,
            'buffer_size': 256,  # Reduced buffer size
            'encoding': 'cp1251'
        }

        # Connection parameters from device or defaults
        if device and hasattr(device, 'connection_string'):
            self._parse_connection_string(device.connection_string)
        else:
            self._set_default_connection()

        self.logger = logging.getLogger(f'fiscal_printer_{self.device_name}')

    def _parse_connection_string(self, conn_str: str):
        """Parse connection string for IoT configuration"""
        try:
            if conn_str.startswith('serial:'):
                parts = conn_str.split(':')
                self.conn_type = 'serial'
                self.port = parts[1] if len(parts) > 1 else '/dev/ttyUSB0'
                self.baudrate = int(parts[2]) if len(parts) > 2 else 115200

            elif conn_str.startswith('tcp:'):
                parts = conn_str.split(':')
                self.conn_type = 'tcp'
                self.host = parts[1] if len(parts) > 1 else '192.168.1.100'
                self.port_tcp = int(parts[2]) if len(parts) > 2 else 8000
                self.password = parts[3] if len(parts) > 3 else ''

        except (ValueError, IndexError):
            self.logger.warning(f"Invalid connection string: {conn_str}")
            self._set_default_connection()

    def _set_default_connection(self):
        """Set default connection parameters"""
        self.conn_type = 'serial'
        self.port = '/dev/ttyUSB0'
        self.baudrate = 115200

    def connect(self) -> bool:
        """Establish connection with optimized error handling"""
        try:
            with self.lock:
                if self.conn_type == 'serial' and serial:
                    self.connection = serial.Serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        bytesize=8,
                        parity=serial.PARITY_NONE,
                        stopbits=1,
                        timeout=self.config['timeout']
                    )

                elif self.conn_type == 'tcp' and socket:
                    self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.connection.settimeout(self.config['timeout'])
                    self.connection.connect((self.host, self.port_tcp))

                    if hasattr(self, 'password') and self.password:
                        pwd_data = self.password.encode() + b'\x0A'
                        self.connection.send(pwd_data)

                if ODOO_IOT:
                    self._update_status('connected')

                return True

        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Connection failed: {e}")
            if ODOO_IOT:
                self._update_status('error', str(e))
            return False

    def disconnect(self):
        """Clean disconnect"""
        with self.lock:
            if self.connection:
                try:
                    self.connection.close()
                except:
                    pass
                self.connection = None

            if ODOO_IOT:
                self._update_status('disconnected')

    def _update_status(self, status: str, message: str = ''):
        """Update IoT status if available"""
        if ODOO_IOT:
            event_manager.device_changed(self)

    def _build_message(self, command: int, data: str = "") -> bytes:
        """Build protocol message with memory optimization"""
        data_bytes = data.encode(self.config['encoding'])
        length = 3 + len(data_bytes)
        len_byte = length + 0x20

        nbl_byte = self.message_counter
        self.message_counter = (self.message_counter + 1)
        if self.message_counter > 0x9F:
            self.message_counter = 0x20

        # Build core message
        msg_core = bytes([len_byte, nbl_byte, command]) + data_bytes

        # Calculate XOR checksum
        checksum = 0
        for byte in msg_core:
            checksum ^= byte

        # Convert to ASCII
        cs_high = ((checksum >> 4) & 0x0F) + 0x30
        cs_low = (checksum & 0x0F) + 0x30

        return bytes([0x02]) + msg_core + bytes([cs_high, cs_low, 0x0A])

    def _send_command(self, command: int, data: str = "") -> Optional[str]:
        """Send command with minimal retry logic"""
        if not self.connection:
            raise FiscalPrinterError("DISCONNECTED", "Not connected")

        message = self._build_message(command, data)

        for attempt in range(self.config['max_retries']):
            try:
                with self.lock:
                    if self.conn_type == 'serial':
                        self.connection.write(message)
                        response = self.connection.read(self.config['buffer_size'])
                    else:
                        self.connection.send(message)
                        response = self.connection.recv(self.config['buffer_size'])

                return self._parse_response(response)

            except FiscalPrinterError as e:
                if e.error_code == "RETRY" and attempt < self.config['max_retries'] - 1:
                    time.sleep(0.1)
                    continue
                raise
            except Exception as e:
                self.last_error = str(e)
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(0.1)
                    continue
                raise FiscalPrinterError("COMMUNICATION", str(e))

    def _parse_response(self, response: bytes) -> Optional[str]:
        """Parse response with compact error handling"""
        if len(response) < 1:
            raise FiscalPrinterError("TIMEOUT", "No response")

        if response[0] == 0x06:  # ACK
            if len(response) >= 4:
                status = chr(response[2]) + chr(response[3])
                if status != "30":
                    error_msg = self.ERROR_CODES.get(chr(response[2]) + "0", "Unknown error")
                    raise FiscalPrinterError(status, error_msg)
            return None

        elif response[0] == 0x15:  # NACK
            raise FiscalPrinterError("NACK", "Invalid message")

        elif response[0] == 0x0E:  # RETRY
            raise FiscalPrinterError("RETRY", "Device busy")

        elif response[0] == 0x02:  # Data response
            if len(response) > 4:
                try:
                    length = response[1] - 0x20
                    if length > 3:
                        data = response[4:4 + length - 3].decode(self.config['encoding'])
                        return data
                except (UnicodeDecodeError, IndexError):
                    pass
            return ""

        raise FiscalPrinterError("PROTOCOL", "Invalid response")

    # Core fiscal operations - optimized for IoT

    def get_status(self) -> Dict[str, Union[str, bool]]:
        """Get printer status"""
        try:
            self._send_command(0x20)
            return {"status": "ready", "connected": True}
        except FiscalPrinterError as e:
            return {"status": "error", "error": e.message, "connected": False}

    def open_receipt(self, operator: str = "1", password: str = "000000") -> bool:
        """Open fiscal receipt with minimal parameters"""
        try:
            data = f"{operator};{password};1;1;0"  # Detailed, with VAT, step-by-step
            self._send_command(0x30, data)
            if ODOO_IOT:
                self._update_status('receipt_open')
            return True
        except FiscalPrinterError:
            return False

    def add_item(self, name: str, price: float, vat: VATClass = VATClass.VAT_A,
                 qty: float = 1.0) -> bool:
        """Add item to receipt"""
        try:
            # Truncate name for memory efficiency
            name = name[:34].replace(';', ' ')
            data = f"{name};{vat.value};{price:.2f}"

            if qty != 1.0:
                data += f"*{qty:.3f}"

            self._send_command(0x31, data)
            return True
        except FiscalPrinterError:
            return False

    def add_payment(self, amount: float, payment_type: PaymentType = PaymentType.CASH) -> bool:
        """Add payment to receipt"""
        try:
            data = f"{payment_type.value};0;{amount:.2f}"
            self._send_command(0x35, data)
            return True
        except FiscalPrinterError:
            return False

    def close_receipt(self) -> bool:
        """Close receipt"""
        try:
            self._send_command(0x38)
            if ODOO_IOT:
                self._update_status('receipt_closed')
            return True
        except FiscalPrinterError:
            return False

    def cancel_receipt(self) -> bool:
        """Cancel receipt"""
        try:
            self._send_command(0x39)
            if ODOO_IOT:
                self._update_status('receipt_cancelled')
            return True
        except FiscalPrinterError:
            return False

    def cash_payment_close(self) -> bool:
        """Pay exact amount and close (most common operation)"""
        try:
            self._send_command(0x36)
            if ODOO_IOT:
                self._update_status('receipt_closed')
            return True
        except FiscalPrinterError:
            return False

    # IoT specific methods

    def print_receipt(self, receipt_data: Dict) -> Dict[str, Union[bool, str]]:
        """
        Main method for printing receipt from IoT/POS
        Expected format:
        {
            'operator': '1',
            'password': '000000',
            'items': [
                {'name': 'Product', 'price': 10.0, 'qty': 1.0, 'vat': 'А'},
                ...
            ],
            'payments': [
                {'amount': 10.0, 'type': 'cash'},
                ...
            ]
        }
        """
        result = {'success': False, 'error': ''}

        try:
            # Open receipt
            operator = receipt_data.get('operator', '1')
            password = receipt_data.get('password', '000000')

            if not self.open_receipt(operator, password):
                raise FiscalPrinterError("RECEIPT", "Cannot open receipt")

            # Add items
            for item in receipt_data.get('items', []):
                name = item.get('name', 'Item')
                price = float(item.get('price', 0))
                qty = float(item.get('qty', 1))
                vat_str = item.get('vat', 'А')

                # Convert VAT string to enum
                vat_class = VATClass.VAT_A
                for vat in VATClass:
                    if vat.value == vat_str:
                        vat_class = vat
                        break

                if not self.add_item(name, price, vat_class, qty):
                    raise FiscalPrinterError("ITEM", f"Cannot add item: {name}")

            # Process payments
            payments = receipt_data.get('payments', [])
            if payments:
                for payment in payments:
                    amount = float(payment.get('amount', 0))
                    pay_type_str = payment.get('type', 'cash').lower()

                    # Map payment type
                    pay_type = PaymentType.CASH
                    if pay_type_str in ['card', 'credit']:
                        pay_type = PaymentType.CARD
                    elif pay_type_str in ['bank', 'transfer']:
                        pay_type = PaymentType.BANK

                    if not self.add_payment(amount, pay_type):
                        raise FiscalPrinterError("PAYMENT", f"Cannot add payment: {amount}")

                # Close receipt
                if not self.close_receipt():
                    raise FiscalPrinterError("CLOSE", "Cannot close receipt")
            else:
                # No explicit payments - use cash and close
                if not self.cash_payment_close():
                    raise FiscalPrinterError("CLOSE", "Cannot close with cash payment")

            result['success'] = True

        except FiscalPrinterError as e:
            result['error'] = e.message
            # Try to cancel receipt on error
            try:
                self.cancel_receipt()
            except:
                pass

        except Exception as e:
            result['error'] = str(e)
            try:
                self.cancel_receipt()
            except:
                pass

        return result

    def daily_report(self, z_report: bool = False) -> Dict[str, Union[bool, str]]:
        """Print daily report (X or Z)"""
        try:
            option = "Z" if z_report else "X"
            self._send_command(0x7C, option)
            return {'success': True}
        except FiscalPrinterError as e:
            return {'success': False, 'error': e.message}

    # IoT Discovery and identification

    @classmethod
    def supported_devices(cls):
        """Return list of supported device identifiers for IoT discovery"""
        return [
            {'vendor_id': 0x0403, 'product_id': 0x6001},  # FTDI USB-Serial
            {'vendor_id': 0x067b, 'product_id': 0x2303},  # Prolific USB-Serial
        ]

    @classmethod
    def get_device_type(cls):
        """Return device type for IoT"""
        return 'fiscal_printer'

    def get_device_info(self) -> Dict:
        """Get device information for IoT dashboard"""
        info = {
            'name': self.device_name,
            'type': 'fiscal_printer',
            'status': 'disconnected',
            'last_error': self.last_error
        }

        if self.connection:
            info['status'] = 'connected'
            try:
                version_data = self._send_command(0x21)
                if version_data:
                    parts = version_data.split(';')
                    info['model'] = parts[3] if len(parts) > 3 else 'Unknown'
                    info['version'] = parts[4] if len(parts) > 4 else 'Unknown'
            except:
                pass

        return info


# Standalone test functions for development
def test_fiscal_printer():
    """Test function for development"""
    printer = BulgarianFiscalDriver()

    if printer.connect():
        print("Connected successfully")

        # Test receipt
        receipt = {
            'items': [
                {'name': 'Test Item', 'price': 1.20, 'qty': 2, 'vat': 'А'}
            ]
        }

        result = printer.print_receipt(receipt)
        print(f"Receipt result: {result}")

        printer.disconnect()
    else:
        print("Connection failed")


if __name__ == "__main__":
    test_fiscal_printer()
