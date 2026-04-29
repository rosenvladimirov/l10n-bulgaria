# ErpNet.FP Пълна Имплементация за Odoo 18 POS

## 📋 Съдържание

1. [Преглед на имплементацията](#преглед)
2. [Нови функции](#нови-функции)
3. [Примери за употреба](#примери)
4. [API Референция](#api)
5. [Законови изисквания](#законови-изисквания)

---

## 🎯 Преглед

Пълна имплементация на всички ErpNet.FP функции за българските фискални принтери в Odoo 18 POS.

### Какво е ново:

✅ **Основни функции** (имаше ги преди):
- `printReceipt()` - Печат на фискален бон
- `openCashbox()` - Отваряне на касов чекмедже
- `_formatUniqueSaleNumber()` - Правилен формат на уникален номер

✅ **НОВИ критични функции** (законово задължителни):
- `printReversalReceipt()` - Сторно бон (връщане на стока) 🔴
- `printZReport()` - Дневен фискален отчет 🔴

✅ **НОВИ важни функции**:
- `printXReport()` - Междинен отчет
- `depositMoney()` - Служебно вкарване на пари
- `withdrawMoney()` - Служебно изкарване на пари
- `getStatus()` - Real-time проверка на статус
- `getPrinterInfo()` - Информация за принтера
- `getCurrentCash()` - Текуща сума в касата
- `printLastReceiptDuplicate()` - Дубликат на последния бон

✅ **Разширена поддръжка**:
- Operator credentials (оператор + парола)
- Info section (информация за клиент)
- Различни item types (comment, footer-comment, etc.)

---

## 🆕 Нови функции

### 1. Сторно бон (Reversal Receipt) 🔴 КРИТИЧНО!

**Законово изискване**: В България е задължително да се поддържа сторниране на бонове.

```javascript
const fiscalPrinter = new ErpNetFPPrinter(this.env, {
    baseUrl: "https://erpnet.local",
    printerId: "dt737851"
});

// Съхраняваме данните от оригиналния бон
const originalReceipt = {
    uniqueSaleNumber: "DT737851-0001-0000001",
    receiptNumber: "0000085",
    receiptDateTime: "2024-11-01T15:30:00",
    fiscalMemorySerialNumber: "02517985"
};

// Печатаме сторно бон
const result = await fiscalPrinter.printReversalReceipt(
    originalReceipt,
    returnOrder,  // Order с връщаните продукти
    "refund"      // Причина: "operator-error", "refund", "tax-base-reduction"
);

if (result.successful) {
    console.log("Сторно бон отпечатан:", result.fiscalData.receiptNumber);
}
```

### 2. Z Отчет (дневен) 🔴 КРИТИЧНО!

**Законово изискване**: Задължителен в края на работния ден.

```javascript
// В края на деня
const result = await fiscalPrinter.printZReport("1", "0000");

if (result.successful) {
    console.log("Z отчет отпечатан успешно!");
}
```

### 3. X Отчет (междинен)

```javascript
// По всяко време през деня за проверка на оборот
const result = await fiscalPrinter.printXReport("1", "0000");
```

### 4. Служебно вкарване/изкарване на пари

```javascript
// Начална каса в началото на деня
await fiscalPrinter.depositMoney(100.00, "Начална каса");

// Изкарване за разход
await fiscalPrinter.withdrawMoney(50.00, "Дребни пари");
```

### 5. Проверка на статус

```javascript
// Real-time проверка
const status = await fiscalPrinter.getStatus();

if (status.online) {
    console.log("Принтерът е онлайн");
    console.log("Време:", status.deviceDateTime);
} else {
    console.log("Принтерът е офлайн!");
}
```

### 6. Текуща сума в касата

```javascript
const cashInfo = await fiscalPrinter.getCurrentCash();

if (cashInfo.successful) {
    console.log("Сума в касата:", cashInfo.amount, "лв");
}
```

### 7. Дубликат на последния бон

```javascript
// Клиент иска още едно копие
await fiscalPrinter.printLastReceiptDuplicate();
```

---

## 📚 Примери за употреба

### Пълен workflow за работен ден

```javascript
const fiscalPrinter = new ErpNetFPPrinter(this.env, {
    baseUrl: this.pos.session.l10n_bg_erp_net_fp_host,
    printerId: this.pos.session.l10n_bg_erp_net_fp_ip
});

// 1️⃣ СУТРИН - Отваряне на смяна
await fiscalPrinter.depositMoney(100.00, "Начална каса");

// 2️⃣ ПО ВРЕМЕ НА ДЕНЯ - Продажби
const saleResult = await fiscalPrinter.printReceipt(order);

if (saleResult.successful) {
    // Запазваме fiscal данните за евентуално сторниране
    order.l10n_bg_fiscal_receipt_number = saleResult.fiscalData.receiptNumber;
    order.l10n_bg_fiscal_memory_number = saleResult.fiscalData.fiscalMemorySerialNumber;
    order.l10n_bg_unique_sale_number = receiptData.uniqueSaleNumber;
}

// 3️⃣ СТОРНИРАНЕ (ако е нужно)
if (customerWantsRefund) {
    const reversalResult = await fiscalPrinter.printReversalReceipt(
        {
            uniqueSaleNumber: order.l10n_bg_unique_sale_number,
            receiptNumber: order.l10n_bg_fiscal_receipt_number,
            receiptDateTime: order.date_order,
            fiscalMemorySerialNumber: order.l10n_bg_fiscal_memory_number
        },
        returnOrder,
        "refund"
    );
}

// 4️⃣ МЕЖДИННА ПРОВЕРКА
await fiscalPrinter.printXReport();

// 5️⃣ ВЕЧЕРТА - Затваряне на смяна
await fiscalPrinter.printZReport("1", "0000");
```

### Интеграция с payment_screen.js

```javascript
// В payment_screen.js - след успешен fiscal печат
if (result.successful) {
    // Запазваме всички fiscal данни в order-а
    order.l10n_bg_fiscal_receipt_number = result.fiscalData?.receiptNumber;
    order.l10n_bg_fiscal_memory_number = result.fiscalData?.fiscalMemorySerialNumber;
    order.l10n_bg_unique_sale_number = receiptData.uniqueSaleNumber;
    order.l10n_bg_is_fiscalized = true;
    
    // За по-късно сторниране трябва да запазим и датата
    order.l10n_bg_fiscal_receipt_datetime = new Date().toISOString();
}
```

### Добавяне на коментари в бона

```javascript
// В _prepareFiscalReceiptData() можеш да добавиш коментари:

// След всеки продукт
items.push({
    text: "Продукт 1",
    quantity: 1,
    unitPrice: 10,
    taxGroup: 2
});

items.push({
    type: "comment",
    text: "Специална промоция!"
});

// В края на бона
items.push({
    type: "footer-comment",
    text: "БЛАГОДАРИМ ВИ ЗА ПОКУПКАТА!"
});
```

### Отстъпка по сума (не процент)

```javascript
items.push({
    type: "discount-amount",
    amount: 5.00  // 5 лв отстъпка на целия бон
});
```

---

## 🔧 API Референция

### Конструктор

```javascript
new ErpNetFPPrinter(env, params)
```

**Параметри**:
- `env` - Odoo environment
- `params.baseUrl` - ErpNet.FP server URL (например "https://erpnet.local")
- `params.printerId` - Printer ID (например "dt737851")

### Методи

#### printReceipt(order, options)
Печат на фискален бон.

**Параметри**:
- `order` - POS Order обект
- `options` (optional):
  - `operator` - Оператор ID
  - `operatorPassword` - Парола
  - `info` - Допълнителна информация

**Връща**: `Promise<{successful, fiscalData}>`

#### printReversalReceipt(originalReceipt, order, reason)
Сторно бон.

**Параметри**:
- `originalReceipt` - Данни от оригиналния бон
  - `uniqueSaleNumber`
  - `receiptNumber`
  - `receiptDateTime`
  - `fiscalMemorySerialNumber`
- `order` - POS Order с връщаните продукти
- `reason` - "operator-error" | "refund" | "tax-base-reduction"

**Връща**: `Promise<{successful, fiscalData}>`

#### printXReport(operator, operatorPassword)
Междинен отчет (без нулиране).

**Връща**: `Promise<{successful}>`

#### printZReport(operator, operatorPassword)
Дневен фискален отчет (с нулиране).

**Връща**: `Promise<{successful}>`

#### depositMoney(amount, text)
Служебно вкарване на пари.

**Връща**: `Promise<{successful}>`

#### withdrawMoney(amount, text)
Служебно изкарване на пари.

**Връща**: `Promise<{successful}>`

#### getStatus()
Проверка на статус.

**Връща**: `Promise<{successful, online, deviceDateTime, messages}>`

#### getPrinterInfo()
Информация за принтера.

**Връща**: `Promise<{successful, info}>`

#### getCurrentCash()
Текуща сума в касата.

**Връща**: `Promise<{successful, amount}>`

#### printLastReceiptDuplicate()
Дубликат на последния бон.

**Връща**: `Promise<{successful}>`

#### openCashbox()
Отваряне на касов чекмедже.

**Връща**: `Promise<boolean>`

---

## ⚖️ Законови изисквания в България

### 🔴 Задължителни функции:

1. **Сторниране на бонове** (`printReversalReceipt`)
   - Законово изискване по чл. 118, ал. 3 от ЗДДС
   - Трябва да може да сторнира всеки фискален бон

2. **Дневен Z отчет** (`printZReport`)
   - Задължителен в края на всеки работен ден
   - Законово изискване по Наредба Н-18

3. **Съхранение на фискални данни**
   - `receiptNumber` - Номер на бон
   - `fiscalMemorySerialNumber` - Номер на фискална памет
   - `uniqueSaleNumber` - Уникален номер на продажбата
   - Трябва да се съхраняват за евентуално сторниране

### ⚠️ Важни бележки:

- При сторниране `uniqueSaleNumber` трябва да е **същия** като оригиналния бон
- Z отчет **нулира** текущите суми - извършва се само веднъж в края на деня
- X отчет **не нулира** - може да се извършва по всяко време

---

## 🔄 Разлики между старата и новата версия

### Преди (стара версия):

```javascript
// Само 2 метода
✅ printReceipt()
✅ openCashbox()
```

### След (нова версия):

```javascript
// 12 метода!
✅ printReceipt() - подобрен с operator credentials и info
✅ openCashbox()
🆕 printReversalReceipt() - сторно бон
🆕 printXReport() - междинен отчет
🆕 printZReport() - дневен отчет
🆕 depositMoney() - вкарване на пари
🆕 withdrawMoney() - изкарване на пари
🆕 getStatus() - проверка на статус
🆕 getPrinterInfo() - информация за принтера
🆕 getCurrentCash() - текуща сума
🆕 printLastReceiptDuplicate() - дубликат
🆕 _extractErrorMessages() - helper за errors
```

---

## 🚀 Как да използвам новата версия

### Стъпка 1: Замени стария файл

```bash
# Backup на стария файл
cp erp_net_fp_printer.js erp_net_fp_printer.js.backup

# Копирай новия файл
cp erp_net_fp_printer_full.js erp_net_fp_printer.js
```

### Стъпка 2: Рестартирай Odoo

```bash
sudo systemctl restart odoo
```

### Стъпка 3: Update на модула

В Odoo:
1. Apps → Localization / ErpNet.FP
2. Update

### Стъпка 4: Добави бутони в UI (опционално)

Можеш да добавиш бутони в POS интерфейса за:
- X отчет
- Z отчет
- Дубликат на бон
- Проверка на статус

---

## 📝 Бележки за разработчици

### uniqueSaleNumber формат

Сега използва **Printer ID** като първа част:

```
dt737851 → DT737851-0001-0000001
          └─────┬─────┘ └─┬─┘ └───┬───┘
           Printer ID    POS   Order seq
```

### Error handling

Всички методи връщат консистентен format:

```javascript
{
    successful: true/false,
    message: {
        title: "...",
        body: "..."
    },
    errorCode: "...", // optional
    fiscalData: {...} // при успех
}
```

### Logging

Всички методи логват подробна информация:

```javascript
console.log("[ErpNetFPPrinter] 🎯 Method called");
console.log("[ErpNetFPPrinter] ✅ SUCCESS");
console.log("[ErpNetFPPrinter] ❌ ERROR");
```

---

## 🐛 Често срещани проблеми

### "Invalid format of UniqueSaleNumber"
- ✅ РЕШЕНО в новата версия
- uniqueSaleNumber сега използва правилния формат с Printer ID

### "Order validation blocked"
- Нормално - fiscal печат е задължителен преди да се финализира order
- Проверете връзката с ErpNet.FP server

### Принтерът не отговаря
```javascript
// Провери статус
const status = await fiscalPrinter.getStatus();
console.log("Online:", status.online);
```

---

## 📞 Поддръжка

За въпроси относно ErpNet.FP:
- Facebook група: https://www.facebook.com/groups/BgBusinessDev/
- GitHub: https://github.com/erpnet/ErpNet.FP

---

## 📄 Лиценз

Следва лиценза на ErpNet.FP - BSD Zero Clause License
