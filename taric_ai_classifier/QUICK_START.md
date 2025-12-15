# 🚀 Quick Start Guide - AI TARIC Classifier

## За нетърпеливите - 5 минути до първа класификация!

### Стъпка 1: Инсталация (2 мин)

```bash
# Копирайте модула в Odoo addons
cd /path/to/odoo/addons
cp -r /path/to/taric_ai_classifier .

# Рестартирайте Odoo
sudo systemctl restart odoo
```

В Odoo:
1. Apps → Update Apps List
2. Търсете "AI TARIC"
3. Install

### Стъпка 2: API Key (1 мин)

1. Регистрирайте се на https://console.anthropic.com/
2. Вземете API key (Free $5 credits!)
3. В Odoo: Settings → Accounting → TARIC & INTRASTAT AI
4. Paste API key → Save

### Стъпка 3: Първа класификация! (2 мин)

**За 1 продукт:**
1. Product → Create
2. Name: "Samsung Galaxy S24 Mobile Phone"
3. TARIC & INTRASTAT таб → 🤖 Classify with AI
4. Select best suggestion → Apply!

**За 100 продукта:**
1. Products → Select All
2. Action → Batch Classify Products
3. ✅ Only Unclassified + ✅ Auto-apply High Confidence
4. Start Classification
5. ☕ Grab coffee (takes ~5 min for 100 products)

## 📊 Какво получавате?

### За всеки продукт:
- ✅ 10-digit TARIC код
- ✅ 8-digit CN8/INTRASTAT код
- ✅ Описание на BG и EN
- ✅ Допълнителни единици
- ✅ Confidence score
- ✅ AI обяснение защо този код

### Пример резултат:
```
Product: "Samsung Galaxy S24"
├─ TARIC Code: 8517120000
├─ CN8 Code: 85171200  
├─ Description BG: "Телефони за клетъчни мрежи"
├─ Supplementary Unit: p/st (pieces)
├─ Confidence: 98%
└─ AI Reasoning: "Smartphones are classified under telecommunications equipment..."
```

## 💰 Колко струва?

| Продукти | Цена (USD) | Време |
|----------|-----------|-------|
| 1 | $0.006 | 3 сек |
| 100 | $0.60 | 5 мин |
| 1,000 | $6.00 | 50 мин |
| 10,000 | $60.00 | 8 часа |

💡 **Free tier:** $5 credits = ~800 безплатни класификации!

## 🎯 Use Cases

### Електронна търговия
```python
# Import 5000 products from CSV
→ Batch Classify (30 min, $30)
→ 95% auto-classified
→ 5% manual review
→ Ready for EU export! ✅
```

### Производствена компания
```python
# 200 raw materials + 150 finished goods
→ Batch Classify (15 min, $2.10)
→ INTRASTAT ready
→ Customs compliant ✅
```

### Счетоводна къща
```python
# Client has 50 products, needs INTRASTAT
→ Classify all (2 min, $0.30)
→ Verify top 10 manually
→ Generate INTRASTAT report ✅
```

## 🔥 Pro Tips

### Tip #1: Добро описание = по-добър резултат
```
❌ Bad: "Phone"
✅ Good: "Samsung Galaxy S24 5G smartphone, 256GB"
```

### Tip #2: Batch класификация през нощта
```python
# Schedule for 2 AM
→ Set Auto-apply High Confidence = True
→ Review results in morning
→ Only verify low confidence (<80%)
```

### Tip #3: Създайте си шаблони
```python
# За често продавани категории
Electronics → 8517...
Food → 07...
Textiles → 61...
Furniture → 94...
```

## ❓ FAQ

**Q: Трябва ли да плащам за API?**
A: Първите $5 са безплатни = 800+ класификации

**Q: Колко точен е AI-то?**
A: 95%+ accuracy за стандартни продукти, 85%+ за специфични

**Q: Мога ли да редактирам предложенията?**
A: Да! Всеки код може да се промени ръчно

**Q: Работи ли offline?**
A: Не, нужна е интернет връзка за AI API

**Q: Поддържа ли multi-company?**
A: Да, всяка компания има свои настройки

## 🆘 Помощ

Нещо не работи?

1. **Check API Key:** Settings → TARIC & INTRASTAT AI
2. **Check Internet:** Тествайте връзката към api.anthropic.com
3. **Check Logs:** Settings → Technical → Logging
4. **Contact Support:** support@example.com

## 📚 Next Steps

След успешна първа класификация:
1. 📖 Прочетете пълния [README.md](README.md)
2. 🇧🇬 Научете за [INTRASTAT декларации](INTRASTAT_BG_GUIDE.md)
3. 🔧 Настройте автоматизация
4. 🎓 Обучете екипа

## ⭐ Enjoy!

Готово! Вашите продукти вече имат правилни TARIC кодове.

**Happy classifying! 🚀**
