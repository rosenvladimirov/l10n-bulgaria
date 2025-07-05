from odoo.exceptions import UserError

class FiscalPrinterError(UserError):
    """Базово изключение за фискален принтер"""
    pass

class FiscalPrinterConnectionError(FiscalPrinterError):
    """Изключение при проблеми с връзката"""
    pass

class FiscalPrinterValidationError(FiscalPrinterError):
    """Изключение при невалидни данни"""
    pass

class FiscalPrinterResponseError(FiscalPrinterError):
    """Изключение при грешен отговор от принтера"""
    pass
