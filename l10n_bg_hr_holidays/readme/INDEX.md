# 📁 Съдържание на пакета / Package Contents

## Основни файлове / Core Files

### 1. 📄 `hr_leave_types_bulgaria_complete.xml`
**Размер:** ~35 KB  
**Тип:** XML Data File  
**Описание:** Основен XML файл с всички 61 вида отпуски за импорт в Odoo. Това е главният файл, който трябва да се импортира в системата.

**Съдържа:**
- 17 НЗОК болнични отпуски
- 4 платени годишни отпуски
- 8 отпуска за граждански задължения
- 4 специални отпуски
- 7 отпуска за майчинство и бащинство
- 4 образователни отпуски

---

### 2. 📘 `hr_leave_types_documentation_bg.md`
**Размер:** ~8 KB  
**Тип:** Markdown Documentation  
**Описание:** Пълна документация на български език с подробна информация за всеки тип отпуск.

**Включва:**
- Табли с всички отпуски по категории
- Продължителност и условия
- Изисквания за документи
- Начин на заплащане
- Правни основания

---

### 3. 📗 `quick_reference_bg.md`
**Размер:** ~12 KB  
**Тип:** Quick Reference Guide  
**Описание:** Бърза справка с всички 61 вида отпуски в табличен формат за лесна справка.

**Включва:**
- Пълен списък на всички отпуски
- Кодове и имена
- Статистика по категории
- Цветово кодиране
- Честота на използване

---

### 4. 📙 `README.md`
**Размер:** ~7 KB  
**Тип:** Installation & Usage Guide  
**Описание:** Подробни инструкции за инсталация, конфигурация и използване на модула.

**Включва:**
- 3 метода за инсталация
- Стъпки за конфигурация
- FAQ секция
- Технически подробности

---

### 5. 🐍 `__manifest__.py`
**Размер:** ~2 KB  
**Тип:** Python Module Manifest  
**Описание:** Манифест файл за Odoo модула с метаданни и зависимости.

**Включва:**
- Име и версия на модула
- Описание на функционалност
- Зависимости
- Автор и лиценз

---

### 6. 📜 `CHANGELOG.md`
**Размер:** ~4 KB  
**Тип:** Version History  
**Описание:** История на промените и планирани функционалности.

**Включва:**
- Промени по версии
- Планирани подобрения
- Известни проблеми
- Бележки за обновяване

---

### 7. 📇 `INDEX.md` (този файл)
**Размер:** ~2 KB  
**Тип:** Package Index  
**Описание:** Този файл - индекс на всички файлове в пакета.

---

## Структура на модула / Module Structure

```
hr_holidays_bg/
│
├── __init__.py                              # Python initialization
├── __manifest__.py                          # Module manifest
│
├── data/
│   └── hr_leave_types_bulgaria_complete.xml # Leave types data
│
├── doc/
│   ├── hr_leave_types_documentation_bg.md   # Full documentation
│   ├── quick_reference_bg.md                # Quick reference
│   ├── README.md                            # Installation guide
│   ├── CHANGELOG.md                         # Version history
│   └── INDEX.md                             # This file
│
└── static/
    └── description/
        ├── icon.png                         # Module icon (optional)
        └── index.html                       # Module description (optional)
```

---

## Как да използвате файловете / How to Use

### За краен потребител / For End Users:
1. **Първо прочетете:** `README.md` за инструкции за инсталация
2. **Импортирайте:** `hr_leave_types_bulgaria_complete.xml` в Odoo
3. **За справка:** Използвайте `quick_reference_bg.md`

### За администратори / For Administrators:
1. **Инсталация:** Следвайте `README.md`
2. **Конфигурация:** Вижте `hr_leave_types_documentation_bg.md`
3. **Поддръжка:** Проверявайте `CHANGELOG.md` за обновления

### За разработчици / For Developers:
1. **Манифест:** Редактирайте `__manifest__.py`
2. **XML данни:** Модифицирайте `hr_leave_types_bulgaria_complete.xml`
3. **Документация:** Актуализирайте `.md` файловете

---

## Допълнителни ресурси / Additional Resources

### Онлайн документация
- [Odoo HR Documentation](https://www.odoo.com/documentation/16.0/applications/hr.html)
- [Кодекс на труда](https://lex.bg/laws/ldoc/1594373121)
- [НЗОК стандарти](https://www.nhif.bg/)

### Свържете се с нас / Contact Us
- Email: support@yourcompany.com
- Website: https://www.yourcompany.com
- Forum: https://www.odoo.com/forum

---

## Файлова статистика / File Statistics

| Файл | Тип | Размер | Редове | Описание |
|------|-----|--------|--------|----------|
| hr_leave_types_bulgaria_complete.xml | XML | ~35 KB | ~600 | Основни данни |
| hr_leave_types_documentation_bg.md | MD | ~8 KB | ~250 | Документация |
| quick_reference_bg.md | MD | ~12 KB | ~350 | Бърза справка |
| README.md | MD | ~7 KB | ~220 | Инструкции |
| __manifest__.py | PY | ~2 KB | ~70 | Манифест |
| CHANGELOG.md | MD | ~4 KB | ~150 | История |
| INDEX.md | MD | ~2 KB | ~80 | Индекс |
| **ОБЩО** | **-** | **~70 KB** | **~1720** | **7 файла** |

---

## Версия / Version
**Пакет:** Bulgarian Leave Types for Odoo v1.0.0  
**Дата:** 31 октомври 2025  
**Съвместимост:** Odoo 14.0+  
**Лиценз:** LGPL-3.0

---

## Бързи връзки / Quick Links

🔗 [README](README.md) - Как да започнете  
🔗 [Документация](hr_leave_types_documentation_bg.md) - Пълна информация  
🔗 [Бърза справка](quick_reference_bg.md) - Списък на отпуските  
🔗 [XML Data](hr_leave_types_bulgaria_complete.xml) - Файл за импорт  
🔗 [Промени](CHANGELOG.md) - История на версиите  

---

**Благодарим, че избрахте нашия модул! 🎉**
