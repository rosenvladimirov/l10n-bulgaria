# 🤖 AI TARIC & INTRASTAT Classifier for Odoo

Автоматична класификация на стоки със TARIC и INTRASTAT кодове, използвайки изкуствен интелект (Claude AI).

## 📋 Описание

Този модул предоставя напълно автоматизирана система за класификация на продукти с митнически TARIC кодове и INTRASTAT номенклатура за България. Използва се най-новата AI технология (Claude Sonnet 4.5) от Anthropic за интелигентно разпознаване и предлагане на подходящи кодове.

## ✨ Възможности

### AI Класификация
- 🎯 **Автоматично предлагане** на TARIC кодове чрез AI анализ
- 🔍 **Интелигентно търсене** в TARIC базата данни
- 📊 **Confidence scoring** - оценка на увереността на AI (0-100%)
- 💡 **Обяснение на класификацията** - AI обяснява защо е избрал даден код
- 🇧🇬 **Двуезично** - Подръжка на български и английски език

### TARIC Кодове
- 📚 10-digit TARIC код (CN8 + 2 допълнителни цифри)
- 🏷️ 8-digit Combined Nomenclature (CN8) код
- 💰 Митнически мита и тарифи
- 📦 Допълнителни единици (supplementary units)
- ✅ Онлайн верификация спрямо официалната EU TARIC база
- 📖 История на всички класификации

### INTRASTAT Номенклатура (България)
- 📊 CN8 кодове за INTRASTAT отчитане
- 🇪🇺 Съответствие с изискванията на НСИ България
- 💶 Прагове за деклариране (dispatch/arrival)
- 📝 Код на характера на сделката
- 🚚 Условия на доставка (INCOTERMS)
- ⚖️ Нетно тегло, допълнителни единици, и други задължителни полета

### Batch Обработка
- 📦 **Масова класификация** - обработка на стотици продукти наведнъж
- 🎚️ **Филтри** - само некласифицирани, по категория и др.
- ⚡ **Автоматично прилагане** на високо доверителни предложения (>90%)
- 📈 **Progress tracking** - следене на прогреса в реално време

## 🔧 Инсталация

### Изисквания
- Odoo 16.0, 17.0 или 18.0
- Python 3.8+
- Anthropic API Key (безплатен trial налични на https://console.anthropic.com/)

### Стъпки за инсталация

1. **Копирайте модула** в addons директорията на Odoo:
```bash
cd /path/to/odoo/addons
git clone <repository-url> taric_ai_classifier
# или просто копирайте директорията
```

2. **Рестартирайте Odoo** сървъра:
```bash
sudo systemctl restart odoo
# или
./odoo-bin --addons-path=/path/to/addons
```

3. **Активирайте модула**:
   - Влезте в Odoo като администратор
   - Отидете на Apps
   - Натиснете "Update Apps List"
   - Потърсете "AI TARIC & INTRASTAT"
   - Натиснете "Install"

4. **Конфигурирайте API ключа**:
   - Отидете на Settings → Accounting → TARIC & INTRASTAT AI
   - Въведете вашия Anthropic API Key
   - Запазете настройките

## 🚀 Използване

### Класификация на един продукт

1. Отворете продукт (Product → Products)
2. Отидете на таба "TARIC & INTRASTAT"
3. Натиснете бутона "🤖 Classify with AI"
4. AI ще анализира продукта и ще предложи 3-5 най-подходящи кодове
5. Прегледайте предложенията с техните confidence scores и обяснения
6. Изберете най-подходящия код или въведете ръчно
7. Натиснете "Apply Classification"

### Масова (Batch) класификация

1. Отидете на Product → Products
2. Изберете продуктите, които искате да класифицирате (checkbox)
3. Action → Batch Classify Products
4. Изберете опциите:
   - ✅ Only Unclassified - само продукти без TARIC код
   - 📁 Category Filter - само от определена категория
   - ⚡ Auto-apply High Confidence - автоматично прилагане при >90% confidence
5. Натиснете "Start Classification"
6. Следете прогреса и прегледайте резултатите

### Верификация на код

1. Отворете продукт с присвоен TARIC код
2. Натиснете "✓ Verify Code Online"
3. Системата ще провери кода спрямо официалната EU TARIC база
4. При успех, кодът ще бъде маркиран като "Verified"

### История на класификациите

1. Отворете продукт
2. Натиснете "📋 View History"
3. Ще видите пълна история на всички класификации:
   - Дата и час
   - Метод (AI, Manual, Expert, API)
   - Confidence score
   - Потребител
   - AI reasoning

## ⚙️ Конфигурация

### AI Настройки (Settings → Accounting)

**🤖 AI Classification Settings:**
- **Enable Auto-Classification** - автоматично предлагане при създаване на продукти
- **Minimum Confidence Threshold** - минимален % за показване на предложения (default: 80%)
- **Auto-apply High Confidence** - автоматично прилагане при >95% (default: off)
- **Anthropic API Key** - вашият API ключ

**📊 INTRASTAT Bulgaria Settings:**
- **Threshold - Dispatch (BGN)** - годишен праг за изпращания (default: 500,000)
- **Threshold - Arrival (BGN)** - годишен праг за получавания (default: 500,000)

## 📊 API Структура

### Извикване на AI за класификация

```python
# В Python код
TaricCode = self.env['taric.code']
suggestions = TaricCode.search_by_ai(
    product_description="Високоскоростен WiFi 6 рутер с 4 антени",
    product_category="Electronics"
)

# Резултат:
[
    {
        'code': '8517629000',
        'description_en': 'Other apparatus for transmission or reception of voice...',
        'description_bg': 'Други апарати за предаване или приемане на глас...',
        'confidence': 95,
        'supplementary_unit': 'p/st',
        'reasoning': 'WiFi routers fall under telecommunications equipment...'
    },
    ...
]
```

### Верификация на код

```python
# Верификация спрямо EU база
result = self.env['taric.code'].verify_code_online('8517629000')
# Резултат: {'valid': True, 'description': '...', 'last_updated': '2025-01-15'}
```

### INTRASTAT данни за продукт

```python
# Вземане на INTRASTAT данни
product = self.env['product.product'].browse(product_id)
data = product.get_intrastat_data()
# Резултат:
{
    'product_id': 123,
    'cn8_code': '85171200',
    'description': 'Mobile phone Samsung Galaxy',
    'country_of_origin': 'KR',
    'supplementary_unit': 'p/st',
    'supplementary_quantity': 1.0,
    'net_weight_kg': 0.19,
    'transaction_code': '11',
}
```

## 🔐 Security / Access Rights

Модулът използва стандартните Odoo security groups:

- **User (base.group_user)** - може да вижда TARIC кодове, да класифицира продукти
- **Accountant (account.group_account_user)** - може да създава и редактира TARIC кодове
- **Manager (account.group_account_manager)** - пълен достъп, включително изтриване

## 📁 Файлова структура

```
taric_ai_classifier/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── taric_code.py          # TARIC & INTRASTAT кодове, AI логика
│   ├── product.py              # Product extension
│   └── res_config_settings.py # Конфигурация
├── wizard/
│   ├── __init__.py
│   └── taric_classify_wizard.py # Wizards за класификация
├── views/
│   ├── product_views.xml       # Product форми и списъци
│   ├── taric_code_views.xml    # TARIC форми и менюта
│   ├── intrastat_code_views.xml # INTRASTAT views
│   ├── res_config_settings_views.xml # Настройки
│   └── batch_classify_wizard_views.xml # Batch wizard
├── security/
│   └── ir.model.access.csv     # Access rights
├── data/
│   └── taric_data.xml          # Примерни TARIC кодове
└── README.md
```

## 🎯 Use Cases

### 1. Електронна търговия
- Автоматична класификация на хиляди продукти от каталог
- Бърза подготовка за експорт към ЕС
- Точно изчисление на митнически мита

### 2. Производствени компании
- Класификация на суровини и готови изделия
- INTRASTAT декларации за NSI
- Проследяване на произход на стоките

### 3. Спедиторски фирми
- Проверка и валидация на клиентски TARIC кодове
- Подготовка на митнически документи
- Compliance с EU regulations

### 4. Счетоводни къщи
- Помощ на клиенти с INTRASTAT отчитане
- Бърза класификация при одити
- Експертни заключения с AI подкрепа

## 🧪 Тестване

### Примерни продукти за тестване

```python
# Тест 1: Храна
Product: "Пресни домати розови, високо качество"
Expected: 07020000 (Tomatoes, fresh or chilled)

# Тест 2: Електроника
Product: "iPhone 15 Pro Max 256GB Titanium"
Expected: 85171200 (Cellular phones)

# Тест 3: Текстил
Product: "Памучна бяла тениска, размер L"
Expected: 61091000 (T-shirts, cotton, knitted)

# Тест 4: Мебели
Product: "Дъбово легло с табла 160x200см"
Expected: 94035000 (Wooden bedroom furniture)
```

## 🐛 Troubleshooting

### Грешка: "Anthropic API key not configured"
**Решение:** Отидете на Settings → Accounting → TARIC & INTRASTAT AI и въведете API ключ

### Грешка: "AI service error: 401"
**Решение:** API ключът е невалиден. Проверете дали сте го копирали правилно от Anthropic Console

### AI не предлага кодове
**Решение:** 
- Проверете дали продуктът има име и описание
- Опитайте с по-детайлно описание
- Проверете интернет връзката

### Бавна класификация
**Причина:** AI заявките отнемат 2-5 секунди per продукт
**Решение:** Използвайте batch класификация през нощта или в свободно време

## 💰 Разходи

### Anthropic API Pricing (2025)
- Claude Sonnet 4.5: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- Една класификация: ~500 tokens input + 300 tokens output
- **Цена на класификация: ~$0.006 (1.1 цента)**
- **За 1000 продукти: ~$6.00**
- **За 10,000 продукти: ~$60.00**

💡 **Free Trial:** Anthropic предлага $5 free credits при регистрация!

## 🔄 Roadmap / Бъдещи възможности

- [ ] Интеграция с EU TARIC API (когато стане публично достъпен)
- [ ] Автоматично генериране на INTRASTAT декларации за NSI
- [ ] Интеграция с ErpNet.FP за митнически документи
- [ ] Machine Learning модел за локално обучение
- [ ] Mobile app за сканиране на баркодове и класификация
- [ ] Bulk export/import на TARIC кодове
- [ ] Интеграция с европейски митнически системи (ATLAS, etc.)
- [ ] Автоматични update-и на TARIC база от EC

## 📞 Поддръжка

За въпроси, bugs или feature requests:
- GitHub Issues: [repository-url]/issues
- Email: support@example.com
- Odoo Community Forum: [forum-thread-url]

## 📄 Лиценз

LGPL-3 - Free to use, modify and distribute

## 👨‍💻 Автор

**Rosen Vladimirov**
- GitHub: https://github.com/rosenvladimirov
- Odoo Expert & Bulgarian ERP Specialist

## 🙏 Благодарности

- Anthropic за Claude AI API
- Odoo Community за чудесната платформа
- НСИ България за INTRASTAT документация
- EU Commission за TARIC данни

---

**⭐ Ако модулът ви е полезен, не забравяйте да дадете Star на GitHub! ⭐**
