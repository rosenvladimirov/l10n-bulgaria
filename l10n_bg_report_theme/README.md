# 🎨 Ръководство за цветове в Layout Sections Theme

Този документ описва подробно как се използват цветовите променливи в темата за доклади.

## 📋 Съдържание

- [Цветови променливи](#цветови-променливи)
- [Използване по компоненти](#използване-по-компоненти)
- [Визуална схема](#визуална-схема)
- [Примери за персонализация](#примери-за-персонализация)

---

## 🎨 Цветови променливи

### Дефиниция на променливите
```
scss
$o-default-report-primary-color: rgb(0, 68, 122);           // #00447A - Тъмно синьо
$o-default-report-secondary-color: rgb(245, 245, 245);      // #F5F5F5 - Светло сиво
$o-default-report-inverse-color: rgb(255, 255, 255);        // #FFFFFF - Бяло
$o-default-report-base-color: rgb(128, 128, 128);           // #808080 - Сиво
$o-default-report-footer-background-color: rgb(248, 252, 255); // #F8FCFF - Светло синьо
$o-default-report-background-color: rgb(133, 169, 245);     // #85A9F5 - Средно синьо
$o-default-report-border-color: rgb(5, 84, 147);            // #055493 - Синьо за рамки
```
### Цветова палитра

| Променлива | Цвят | Hex | Предназначение |
|------------|------|-----|----------------|
| `primary-color` | 🔵 Тъмно синьо | `#00447A` | Акцентни елементи, заглавия, важни текстове |
| `secondary-color` | ⚪ Светло сиво | `#F5F5F5` | Фон на секции, алтернативни редове |
| `inverse-color` | ⬜ Бяло | `#FFFFFF` | Текст на тъмен фон |
| `base-color` | 🔘 Сиво | `#808080` | Основен текст, описания |
| `footer-background-color` | 🔷 Светло синьо | `#F8FCFF` | Фон на информационни блокове |
| `background-color` | 🔹 Средно синьо | `#85A9F5` | Фонови изображения (не се използва в момента) |
| `border-color` | 🟦 Синьо | `#055493` | Рамки, разделители |

---

## 🧩 Използване по компоненти

### 1️⃣ **Header (Хедър)**

**Клас:** `.o_sections_header`
```
scss
border-bottom: 1px solid rgba($o-default-report-border-color, 0.5);
color: $o-default-report-base-color;

h4 {
    color: $o-default-report-primary-color;  // Заглавия на документа
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Долна рамка | `border-color` | 🟦 Синьо (50% прозрачност) | Разделител под хедъра |
| Текст | `base-color` | 🔘 Сиво | Основен текст |
| Заглавия `<h4>` | `primary-color` | 🔵 Тъмно синьо | Име на документа |

---

### 2️⃣ **Footer (Футър)**

**Клас:** `.o_sections_footer`
```
scss
border-top: 1px solid rgba($o-default-report-border-color, 0.5);
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Горна рамка | `border-color` | 🟦 Синьо (50% прозрачност) | Разделител над футъра |

---

### 3️⃣ **Article (Основно съдържание)**

**Клас:** `.o_sections_article`
```
scss
color: $o-default-report-base-color;

h2 span {
    color: $o-default-report-primary-color;
}

#total strong {
    color: $o-default-report-primary-color;
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Основен текст | `base-color` | 🔘 Сиво | Текст в артикъла |
| Заглавия `<h2> <span>` | `primary-color` | 🔵 Тъмно синьо | Важни заглавия |
| Сумарни полета `#total strong` | `primary-color` | 🔵 Тъмно синьо | Общи суми |

---

### 4️⃣ **Информационни блокове**

**Клас:** `.o_sections_information`
```
scss
color: $o-default-report-base-color;
background-color: $o-default-report-footer-background-color;
border: 1px solid rgba($o-default-report-border-color, 0.7);
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Текст | `base-color` | 🔘 Сиво | Текст в информационния блок |
| Фон | `footer-background-color` | 🔷 Светло синьо | Фон на блока |
| Рамка | `border-color` | 🟦 Синьо (70% прозрачност) | Рамка около блока |

---

### 5️⃣ **Етикети (Labels)**

**Клас:** `.o_section_labels`
```
scss
color: $o-default-report-primary-color;
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Текст на етикет | `primary-color` | 🔵 Тъмно синьо | Етикети като "From:", "TIN:" и т.н. |

---

### 6️⃣ **Име на документ**

**Клас:** `.o_sections_name`
```
scss
color: $o-default-report-primary-color;

h4, h6 {
    color: inherit;  // Наследява primary-color
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Заглавие на документ | `primary-color` | 🔵 Тъмно синьо | Номер и тип на документа |

---

### 7️⃣ **Таблици - Deal (Споразумение SUPPLIER/CUSTOMER)**

**Клас:** `.o_sections_deal table`

#### **Thead (Заглавна част)**
```
scss
thead {
    border: 1px solid $o-default-report-border-color;
    tr th {
        border: 1px solid rgba($o-default-report-primary-color, 0.9);
        color: $o-default-report-inverse-color;
        background-color: rgba($o-default-report-primary-color, 0.9);
    }
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Външна рамка на таблицата | `border-color` | 🟦 Синьо | Рамка около `<thead>` |
| Рамки на клетки `<th>` | `primary-color` | 🔵 Тъмно синьо (90% непрозрачност) | Рамки на заглавни клетки |
| Фон на клетки `<th>` | `primary-color` | 🔵 Тъмно синьо (90% непрозрачност) | Фон на "SUPPLIER" и "CUSTOMER" |
| Текст на клетки `<th>` | `inverse-color` | ⬜ Бяло | Текст в заглавните клетки |

#### **Tbody (Тяло на таблицата)**
```
scss
tbody {
    color: $o-default-report-base-color;
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Текст в клетки `<td>` | `base-color` | 🔘 Сиво | Данни за партньорите |

---

### 8️⃣ **Таблици - Article (Основни таблици с продукти/услуги)**

**Клас:** `.o_sections_article table`

#### **Thead (Заглавна част)**
```
scss
thead {
    border: 1px solid $o-default-report-border-color;
    tr th {
        border: 1px solid rgba($o-default-report-primary-color, 0.9) !important;
        color: $o-default-report-inverse-color !important;
        background-color: rgba($o-default-report-primary-color, 0.9) !important;
    }
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Външна рамка | `border-color` | 🟦 Синьо | Рамка около заглавната част |
| Рамки на клетки | `primary-color` | 🔵 Тъмно синьо (90% непрозрачност) | Рамки между колоните |
| Фон на клетки | `primary-color` | 🔵 Тъмно синьо (90% непрозрачност) | Фон на заглавния ред |
| Текст | `inverse-color` | ⬜ Бяло | Имена на колоните |

#### **Tbody (Тяло на таблицата)**
```
scss
tbody {
    color: $o-default-report-base-color;
    tr {
        border-bottom: 1px solid rgba($o-default-report-border-color, 0.1);
    }
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Текст | `base-color` | 🔘 Сиво | Данни за продукти/услуги |
| Рамки между редове | `border-color` | 🟦 Синьо (10% прозрачност) | Разделители между редове |

#### **Специални редове**

**Секции (`.o_line_section`)**
```
scss
&.o_line_section td {
    border-top: 1px solid rgba($o-default-report-border-color, 0.7);
    border-bottom: 1px solid rgba($o-default-report-border-color, 0.7);
    background-color: $o-default-report-secondary-color;
    color: $o-default-report-inverse-color;
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Горна/долна рамка | `border-color` | 🟦 Синьо (70% прозрачност) | Рамки на секционния ред |
| Фон | `secondary-color` | ⚪ Светло сиво | Фон на секцията |
| Текст | `inverse-color` | ⬜ Бяло | Име на секцията |

**Междинни суми (`.is-subtotal`)**
```
scss
&.is-subtotal,
td.o_price_total {
    border-top: 1px solid rgba($o-default-report-border-color, 0.7);
    border-bottom: 1px solid rgba($o-default-report-border-color, 0.7);
    background-color: rgba($o-default-report-secondary-color, 0.1);
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Горна/долна рамка | `border-color` | 🟦 Синьо (70% прозрачност) | Рамки около междинните суми |
| Фон | `secondary-color` | ⚪ Светло сиво (10% прозрачност) | Много светъл фон |

---

### 9️⃣ **Таблици - Total (Обща сума)**

**Клас:** `.row > div > table` или `div#total table`
```
scss
thead tr:first-child,
tr.o_subtotal {
    border-bottom: 1px solid $o-default-report-border-color;
}

tr.o_selection_custom_name td {
    color: $o-default-report-primary-color;
}

tr:last-child td,
tr.o_total td {
    background-color: rgba($o-default-report-primary-color, 0.9);
    color: $o-default-report-inverse-color;
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Разделители | `border-color` | 🟦 Синьо | Рамки между редовете |
| Специални имена | `primary-color` | 🔵 Тъмно синьо | Текст с акцент |
| Фон на общата сума | `primary-color` | 🔵 Тъмно синьо (90% непрозрачност) | Финален ред с общата сума |
| Текст на общата сума | `inverse-color` | ⬜ Бяло | Текст в реда с общата сума |

---

### 🔟 **Таблици - Signatures (Подписи)**

**Клас:** `.o_sections_signatures table`

#### **Thead**
```
scss
thead {
    background-color: rgba($o-default-report-primary-color, 0.1);

    .o_signatures_column_header {
        border: 1px solid $o-default-report-border-color;
        color: $o-default-report-base-color;
        background-color: rgba($o-default-report-primary-color, 0.1) !important;
    }
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Фон на `<thead>` | `primary-color` | 🔵 Тъмно синьо (10% прозрачност) | Много светъл син фон |
| Рамки на клетки | `border-color` | 🟦 Синьо | Рамки около заглавията |
| Текст | `base-color` | 🔘 Сиво | Текст в заглавните клетки |

#### **Tbody**
```
scss
tbody {
    color: $o-default-report-base-color;

    td {
        border: 1px solid rgba($o-default-report-border-color, 0.5);

        strong {
            color: $o-default-report-primary-color;
        }

        small {
            color: $o-default-report-base-color;
        }
    }
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Текст | `base-color` | 🔘 Сиво | Основен текст |
| Рамки | `border-color` | 🟦 Синьо (50% прозрачност) | Рамки на клетките |
| Акцентен текст `<strong>` | `primary-color` | 🔵 Тъмно синьо | Важна информация |
| Малък текст `<small>` | `base-color` | 🔘 Сиво | Допълнителна информация |

#### **Alert блокове**
```
scss
.alert h6 {
    color: $o-default-report-primary-color;
}
```
| Елемент | Променлива | Цвят | Описание |
|---------|-----------|------|----------|
| Заглавия | `primary-color` | 🔵 Тъмно синьо | Заглавия на алерти |

---

## 🖼️ Визуална схема

### Структура на документа
```

┌─────────────────────────────────────────────────────────┐
│  HEADER (o_sections_header)                             │
│  ┌────────────────────────────────────────────────┐     │
│  │ Logo              │ h4 (primary-color)         │     │
│  │                   │ Contact info (base-color)  │     │
│  └────────────────────────────────────────────────┘     │
│  border-bottom: border-color (50%)                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  ARTICLE (o_sections_article)                           │
│                                                         │
│  ┌────────────────────────────────────────────────┐     │
│  │ DEAL TABLE (o_sections_deal)                   │     │
│  │ ┌─────────────────┬──────────────────┐         │     │
│  │ │ CUSTOMER        │ SUPPLIER         │  ◄──────│── primary-color (90%) фон
│  │ │ (inverse-color) │ (inverse-color)  │         │     │  inverse-color текст
│  │ ├─────────────────┼──────────────────┤         │     │
│  │ │ Data            │ Data             │  ◄──────│── base-color текст
│  │ └─────────────────┴──────────────────┘         │     │
│  └────────────────────────────────────────────────┘     │
│                                                         │
│  ┌────────────────────────────────────────────────┐     │
│  │ PRODUCTS TABLE                                 │     │
│  │ ┌─────────┬─────────┬─────────┬─────────┐      │     │
│  │ │ Product │ Qty     │ Price   │ Total   │   ◄──│── primary-color (90%) фон
│  │ │         │         │         │         │      │     │  inverse-color текст
│  │ ├─────────┼─────────┼─────────┼─────────┤      │     │
│  │ │ Item 1  │ 5       │ 10.00   │ 50.00   │   ◄──│── base-color текст
│  │ ├─────────┼─────────┼─────────┼─────────┤      │     │  border-color (10%) разделител
│  │ │ SECTION │         │         │         │   ◄──│── secondary-color фон
│  │ ├─────────┼─────────┼─────────┼─────────┤      │     │  inverse-color текст
│  │ │ Item 2  │ 3       │ 20.00   │ 60.00   │      │     │
│  │ ├─────────┴─────────┴─────────┼─────────┤      │     │
│  │ │ Subtotal                    │ 110.00  │   ◄──│── secondary-color (10%) фон
│  │ ├─────────────────────────────┼─────────┤      │     │
│  │ │ TOTAL                       │ 110.00  │   ◄──│── primary-color (90%) фон
│  │ │                             │         │      │     │  inverse-color текст
│  │ └─────────────────────────────┴─────────┘      │     │
│  └────────────────────────────────────────────────┘     │
│                                                         │
│  ┌────────────────────────────────────────────────┐     │
│  │ SIGNATURES TABLE (o_sections_signatures)       │     │
│  │ ┌─────────────────┬──────────────────┐         │     │
│  │ │ CUSTOMER        │ COMPILER         │  ◄──────│── primary-color (10%) фон
│  │ │                 │                  │         │     │  base-color текст
│  │ ├─────────────────┼──────────────────┤         │     │
│  │ │ Signature space │ Signature space  │         │     │
│  │ │ strong text     │ strong text      │  ◄──────│── primary-color за strong
│  │ └─────────────────┴──────────────────┘         │     │
│  └────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  FOOTER (o_sections_footer)                             │
│  border-top: border-color (50%)                         │
│  ┌────────────────────────────────────────────────┐     │
│  │ Page: 1/3        │ Document info               │     │
│  └────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```
---

## 🔧 Примери за персонализация

### Промяна на основния акцентен цвят

За да промените основния цвят от тъмно синьо на друг цвят (например корпоративен червен):
```
scss
$o-default-report-primary-color: rgb(178, 34, 34);  // #B22222 - Firebrick Red
```
**Това ще промени:**
- Заглавия на документи
- Фон на заглавни редове в таблици
- Етикети
- Акцентни текстове
- Финален ред с общата сума

### Промяна на текстовия цвят

За да направите текста по-тъмен:
```
scss
$o-default-report-base-color: rgb(64, 64, 64);  // #404040 - По-тъмно сиво
```
### Промяна на фона на информационни блокове

За жълтеникав информационен блок:
```
scss
$o-default-report-footer-background-color: rgb(255, 251, 230);  // #FFFBE6
```
### Пълна цветова палитра - Зелена тема
```
scss
$o-default-report-primary-color: rgb(34, 139, 34);           // #228B22 - Forest Green
$o-default-report-secondary-color: rgb(240, 255, 240);       // #F0FFF0 - Honeydew
$o-default-report-inverse-color: rgb(255, 255, 255);         // #FFFFFF - White
$o-default-report-base-color: rgb(85, 85, 85);               // #555555 - Dark Gray
$o-default-report-footer-background-color: rgb(245, 255, 250); // #F5FFFA - Mint Cream
$o-default-report-border-color: rgb(46, 125, 50);            // #2E7D32 - Dark Green
```
---

## 📝 Бележки

- Всички прозрачности се прилагат чрез `rgba()` функция с последен параметър за alpha канал (0.1 = 10%, 0.5 = 50%, 0.9 = 90%)
- Рамките използват различни нива на прозрачност за визуална йерархия
- `!default` позволява променливите да бъдат презаписани от custom SCSS файлове
- Всички цветове са дефинирани в `report_variable_colors.scss`

---

## 🚀 Как да персонализирате

1. Копирайте файла `report_variable_colors.scss`
2. Променете стойностите на променливите
3. Запазете в custom SCSS файл за вашата компания
4. Приложете промените чрез Odoo настройките за доклади

**Важно:** Използвайте формата `rgb(R, G, B)` за дефиниране на цветовете, за да могат да се използват с `rgba()` функция за прозрачност.

---

**Версия:** 1.0
**Последна актуализация:** 2026-01-04
**Съвместимост:** Odoo 19.0
