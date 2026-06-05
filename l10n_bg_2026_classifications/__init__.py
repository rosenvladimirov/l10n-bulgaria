"""Bulgaria 2026 — Payroll Classifications

Year-stamped МОД migration BGN → EUR + НКПД audit.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP

_logger = logging.getLogger(__name__)

YEAR = 2026
DATE_FROM_NEW = f"{YEAR}-01-01"
DATE_TO_OLD = f"{YEAR - 1}-12-31"
EUR_RATE = Decimal("1.95583")  # ЗВЕРБ фиксиран курс
EUR_CONVERSION_NEEDED = True   # 2026 е първата евро година; за 2027+ → False

MOD_FIELDS = (
    "mod_manager",
    "mod_specialist",
    "mod_technician",
    "mod_clerk",
    "mod_service",
    "mod_skilled",
    "mod_operator",
    "mod_elementary",
)

MODULE = "l10n_bg_2026_classifications"

# ЗБДОО 2026 Приложение 1 — МОД (EUR) по КИД код, на дефинираното ниво
# (DEF-MOD). Недефинирани кодове → 0.0 → get_effective_mod наследява.
ZBDOO_2026_MOD = {
    "01": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "01.4": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "01.49": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "02": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "03": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "05": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "06": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "07": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "08": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "09": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.1": {"mod_manager": 759.78, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.2": {"mod_manager": 759.78, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.3": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.4": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.5": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.6": {"mod_manager": 637.58, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.7": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.8": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.9": {"mod_manager": 573.67, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.12": {"mod_manager": 626.84, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.81": {"mod_manager": 584.41, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "10.82": {"mod_manager": 584.41, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "11": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "12": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "13": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "14": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "15": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "16": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "17": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "18": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "19": {"mod_manager": 901.41, "mod_specialist": 669.79, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "20": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "21": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "22": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "23": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "24": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "25": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "26": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "27": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "28": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "29": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "30": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "31": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "32": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "33": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "35": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "35.1": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "35.2": {"mod_manager": 747.0, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "35.3": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "36": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "37": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "38": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "39": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "41": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "42": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "43": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "45": {"mod_manager": 664.17, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "46": {"mod_manager": 664.17, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "46.46": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "47": {"mod_manager": 664.17, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "47.73": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "47.74": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "49": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "49.5": {"mod_manager": 747.0, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "50": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "51": {"mod_manager": 614.06, "mod_specialist": 563.95, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "52": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "53": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "55": {"mod_manager": 647.3, "mod_specialist": 557.31, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "56": {"mod_manager": 647.3, "mod_specialist": 557.31, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "58": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "59": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "60": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "61": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "62": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "63": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "64": {"mod_manager": 812.44, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "65": {"mod_manager": 812.44, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "66": {"mod_manager": 812.44, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "68": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "69": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "70": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "71": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "72": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "73": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "74": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "75": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "77": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "78": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "79": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "80": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "81": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "82": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "84": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "85": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "86": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "86.1": {"mod_manager": 683.09, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "87": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "88": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "90": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "91": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "92": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "93": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "94": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "95": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "96": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "97": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
    "99": {"mod_manager": 550.66, "mod_specialist": 550.66, "mod_technician": 550.66, "mod_clerk": 550.66, "mod_service": 550.66, "mod_skilled": 550.66, "mod_operator": 550.66, "mod_elementary": 550.66},
}


def _to_eur(bgn_value):
    """Convert BGN → EUR per ЗВЕРБ rules: divide then round to 0.01."""
    if not bgn_value:
        return 0.0
    eur = Decimal(str(bgn_value)) / EUR_RATE
    return float(eur.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def post_init_hook(env):
    """Migrate МОД records from BGN to EUR for the new year.

    Behaviour:
      1. Find all `bg.hr.payroll.economic.activity` records that are
         currently active (date_to is False) and have date_from in the
         prior year or earlier;
      2. For each — close the old record (date_to = YEAR-1-12-31) and
         create a clone with date_from = YEAR-01-01 and all mod_*
         fields converted ÷ 1.95583 (rounded to 2 decimals);
      3. Skip if a record already exists with the new date_from for
         the same code (idempotent re-install);
      4. Audit НКПД (no changes for 2026 — log only).
    """
    Activity = env["bg.hr.payroll.economic.activity"]
    NCOP = env["bg.hr.payroll.ncop.classification"]

    # ----- 1. МОД миграция -----
    if EUR_CONVERSION_NEEDED:
        active_records = Activity.search([
            ("date_from", "<=", DATE_TO_OLD),
            ("date_to", "=", False),
            ("active", "=", True),
        ])
        _logger.info(
            "[%s] Found %d active МОД records to migrate BGN->EUR for %d",
            MODULE, len(active_records), YEAR,
        )

        migrated = skipped = 0
        for old_rec in active_records:
            # Idempotency: skip ако вече има record за нашата година + код
            existing = Activity.search([
                ("code", "=", old_rec.code),
                ("level", "=", old_rec.level),
                ("date_from", "=", DATE_FROM_NEW),
            ], limit=1)
            if existing:
                skipped += 1
                continue

            # Close old record
            old_rec.write({"date_to": DATE_TO_OLD})

            # Clone in EUR for new year
            new_vals = {
                "name": old_rec.name,
                "code": old_rec.code,
                "parent_id": old_rec.parent_id.id if old_rec.parent_id else False,
                "level": old_rec.level,
                "active": True,
                "date_from": DATE_FROM_NEW,
            }
            # DEF-MOD: ЗБДОО 2026 Прил.1 (EUR) — НЕ механична BGN->EUR конверсия.
            # Стойности само на дефинираното от ЗБДОО ниво; недефинирани
            # кодове → 0.0, get_effective_mod() наследява от parent (минимум
            # дивизионната стойност 550.66 EUR).
            zbdoo = ZBDOO_2026_MOD.get(old_rec.code)
            for field in MOD_FIELDS:
                new_vals[field] = zbdoo[field] if zbdoo else 0.0

            Activity.create(new_vals)
            migrated += 1

        _logger.info(
            "[%s] МОД migration: %d new EUR records created, "
            "%d skipped (already existed). Old records closed at %s.",
            MODULE, migrated, skipped, DATE_TO_OLD,
        )
    else:
        _logger.info(
            "[%s] EUR_CONVERSION_NEEDED=False - skip МОД migration "
            "(values already in EUR)", MODULE,
        )

    # ----- 2. НКПД audit -----
    ncop_count = NCOP.search_count([])
    _logger.info(
        "[%s] НКПД-2011: %d records present. No structural changes "
        "for %d (last NSI revision was 2011).",
        MODULE, ncop_count, YEAR,
    )
