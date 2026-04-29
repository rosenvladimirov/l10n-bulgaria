#!/bin/bash
echo "=============================================="
echo "  ФИНАЛНО ТЕСТВАНЕ НА MT940 ПАРСЪР"
echo "=============================================="
echo ""

# Test files
PROCREDIT_BUIN="/home/rosen/Свалени/Telegram Desktop/statements_BG71BUIN95611000736591_period_05_01_2026_to_05_01_2026.txt"
PROCREDIT_PRCB="/home/rosen/Свалені/Telegram Desktop/20250912_ 00147_100_BG81PRCB92301017678025.940.txt"
UNICREDIT="/home/rosen/Свалені/Telegram Desktop/2016696620250206230024_3e59befcb99a4ff8ba9cb24b247fc5d3.txt"

echo "1️⃣  ProCredit (BUIN) - ОКТА ЛАЙТ"
echo "----------------------------------------"
python3 test_parser_standalone.py "$PROCREDIT_BUIN" 2>&1 | grep -E "(Bank Format|Account|Statement Number|TRANSACTIONS|✓ Parsing)" | head -6
echo ""

echo "2️⃣  ProCredit (PRCB) - с кирилица"
echo "----------------------------------------"
python3 test_parser_standalone.py "$PROCREDIT_PRCB" 2>&1 | grep -E "(Bank Format|Account|Statement Number|TRANSACTIONS|✓ Parsing)" | head -6
echo ""

echo "3️⃣  UniCredit Bulbank (UNCR)"
echo "----------------------------------------"
python3 test_parser_standalone.py "$UNICREDIT" 2>&1 | grep -E "(Bank Format|Account|Statement Number|TRANSACTIONS|✓ Parsing)" | head -6
echo ""

echo "=============================================="
echo "  ПРОВЕРКА НА payment_ref"
echo "=============================================="
echo ""

# Check payment_ref specifically for fee transactions
echo "Проверка на такси (fee transactions):"
python3 test_parser_standalone.py "$PROCREDIT_BUIN" 2>&1 | grep -B 2 "Transaction #3\|Transaction #6\|Transaction #10" | grep -E "Transaction #|Field 00:" | head -6

echo ""
echo "✅ Всички тестове завършиха!"
