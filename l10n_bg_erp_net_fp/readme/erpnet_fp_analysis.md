# ErpNet.FP Implementation Analysis

## Текущо имплементирани функции ✅

### 1. POST Print Receipt (основен)
- **Endpoint**: `/printers/{printerId}/receipt`
- **Метод**: `printReceipt(order)`
- **Статус**: ✅ Имплементиран
- **Проблеми**: 
  - ❌ Липсва поддръжка за operator credentials
  - ❌ Липсва поддръжка за "info" секция
  - ⚠️ Липсва поддръжка за различни item types

### 2. POST Open Cashbox
- **Endpoint**: `/printers/{printerId}/cashbox`
- **Метод**: `openCashbox()`
- **Статус**: ✅ Имплементиран

### 3. uniqueSaleNumber формат
- **Формат**: `XX123456-YYYY-1234567`
- **Метод**: `_formatUniqueSaleNumber()`
- **Статус**: ✅ Имплементиран (след корекция)

---

## Липсващи критични функции ❌

### 1. POST Print Reversal Receipt (ВАЖНО!)
**Описание**: Печат на сторно бон (връщане на стока)

**Endpoint**: `/printers/{printerId}/reversalreceipt`

**JSON формат**:
```json
{
  "uniqueSaleNumber": "DT279013-0001-0000001",
  "receiptNumber": "0000085",
  "receiptDateTime": "2019-05-17T13:55:18",
  "fiscalMemorySerialNumber": "02517985",
  "reason": "operator-error",
  "items": [...],
  "payments": [...]
}
```

**Важно**: 
- Използва същия `uniqueSaleNumber` като оригиналния бон
- Изисква `receiptNumber`, `receiptDateTime`, `fiscalMemorySerialNumber` от оригиналния бон
- `reason` може да бъде: "operator-error", "refund", "tax-base-reduction"

**Законово изискване**: В България е задължително да се поддържа сторниране!

---

### 2. POST Print X Report
**Описание**: Междинен отчет (без нулиране)

**Endpoint**: `/printers/{printerId}/xreport`

**JSON формат**:
```json
{
  "operator": "1",
  "operatorPassword": "0000"
}
```

**Използване**: Проверка на оборот по време на деня

---

### 3. POST Print Z Report
**Описание**: Дневен фискален отчет (с нулиране)

**Endpoint**: `/printers/{printerId}/zreport`

**JSON формат**:
```json
{
  "operator": "1",
  "operatorPassword": "0000"
}
```

**Законово изискване**: Задължителен в края на деня!

---

### 4. POST Deposit Money
**Описание**: Служебно вкарване на пари в касата

**Endpoint**: `/printers/{printerId}/deposit`

**JSON формат**:
```json
{
  "amount": 100.00,
  "text": "Начална каса"
}
```

---

### 5. POST Withdraw Money
**Описание**: Служебно изкарване на пари от касата

**Endpoint**: `/printers/{printerId}/withdraw`

**JSON формат**:
```json
{
  "amount": 50.00,
  "text": "Разход"
}
```

---

### 6. GET Printer Status
**Описание**: Проверка на статуса на принтера

**Endpoint**: `/printers/{printerId}/status`

**Response**:
```json
{
  "ok": true,
  "deviceDateTime": "2019-05-10T15:50:00",
  "messages": [...]
}
```

**Използване**: Real-time проверка на връзка и статус

---

### 7. GET Printer Info
**Описание**: Информация за принтера

**Endpoint**: `/printers/{printerId}`

**Response**:
```json
{
  "serialNumber": "DT279013",
  "fiscalMemorySerialNumber": "02517985",
  "model": "Datecs FP-2000",
  ...
}
```

---

### 8. GET Current Cash Amount
**Описание**: Текуща сума в касата

**Endpoint**: `/printers/{printerId}/cash`

**Response**:
```json
{
  "ok": true,
  "amount": 1234.56
}
```

---

### 9. POST Print Duplicate
**Описание**: Печат на дубликат на последния бон

**Endpoint**: `/printers/{printerId}/lastreceipt`

**Използване**: Клиент иска още едно копие

---

## Липсващи Item Types в Receipt

Според документацията, `items` може да съдържа различни типове:

### Текущо имплементирани:
- ✅ `"sale"` (default, може да се пропусне)

### Липсващи:
- ❌ `"comment"` - Коментар между артикулите
- ❌ `"footer-comment"` - Коментар в края
- ❌ `"discount-amount"` - Отстъпка по сума (не процент)
- ❌ `"surcharge-amount"` - Надбавка по сума

**Пример**:
```json
{
  "items": [
    {
      "text": "Сирене",
      "quantity": 1,
      "unitPrice": 12,
      "taxGroup": 2
    },
    {
      "type": "comment",
      "text": "Допълнителна информация..."
    },
    {
      "type": "discount-amount",
      "amount": 2.00
    },
    {
      "type": "footer-comment",
      "text": "БЛАГОДАРИМ ВИ!"
    }
  ]
}
```

---

## Липсващи Receipt полета

### Operator Credentials
```json
{
  "operator": "1",
  "operatorPassword": "0000",
  "uniqueSaleNumber": "...",
  "items": [...],
  "payments": [...]
}
```

### Info Section
```json
{
  "uniqueSaleNumber": "...",
  "items": [...],
  "payments": [...],
  "info": {
    "receiptFormat": "default",
    "recipient": {
      "name": "Company Name",
      "bulstat": "123456789",
      "address": "Sofia, Bulgaria"
    }
  }
}
```

---

## Приоритизация на липсващите функции

### 🔴 Критични (законово задължителни):
1. **Print Reversal Receipt** - за сторниране на бонове
2. **Print Z Report** - дневен отчет
3. **Operator credentials** - операторски пароли

### 🟡 Важни (за пълна функционалност):
4. **Print X Report** - междинен отчет
5. **Deposit/Withdraw Money** - служебни операции
6. **Get Printer Status** - real-time мониторинг
7. **Item types** (comment, footer-comment) - за по-добри бонове

### 🟢 Допълнителни (nice-to-have):
8. **Print Duplicate** - дубликат на бон
9. **Get Printer Info** - информация за устройство
10. **Get Current Cash** - текуща сума в касата
11. **Info section** - разширена информация за клиент

---

## Препоръки

1. **Веднага имплементирай**: Reversal Receipt и Z Report (законови изисквания)
2. **След това добави**: X Report, Deposit/Withdraw, Printer Status
3. **Накрая**: Останалите допълнителни функции

Всички функции следват същия pattern като `printReceipt()`:
- POST заявка към `/printers/{printerId}/{endpoint}`
- JSON body с данни
- Обработка на `result.ok` и `result.messages`
