===================================
Markdown Viewer Locale Dropdown
===================================

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

|badge1|

Преглед на локализирани Markdown файлове с dropdown менюта за избор на език, документ и модул.

**Основни функции:**

* **Dropdown меню за избор на език** - Превключване между различни езикови версии
* **Dropdown меню за избор на документ** - Бърз достъп до различни документи
* **Dropdown меню за избор на модул** - Преглед на документация от различни модули
* Автоматично зареждане според избраните настройки
* Fallback към основния файл, ако липсва локализация
* Интегрирана функция за търсене в съдържанието
* Syntax highlighting за code блокове
* Модален прозорец на цял екран

Използване
==========

След инсталиране на модула, добавете snippet-а във вашите изгледи:

.. code-block:: xml

    <t t-call="markdown_viewer_locale_dropdown.markdown_snippet"/>

Или използвайте директно линк:

.. code-block:: xml

    <a href="#" class="o_show_markdown_dropdown" title="Виж документацията">
        <i class="fa fa-book fa-lg"></i>
    </a>

С data атрибути за предварителен избор:

.. code-block:: xml

    <a href="#" class="o_show_markdown_dropdown"
       data-md-file="readme.md"
       data-md-module="your_module_name"
       title="Виж документацията">
        <i class="fa fa-book fa-lg"></i>
    </a>

Структура на файловете
=======================

Създайте Markdown файлове в следната структура:

.. code-block:: text

    your_module/
    └── static/
        └── src/
            └── md/
                ├── readme.md          # Основен файл (fallback)
                ├── readme.bg.md       # Българска версия
                ├── readme.en.md       # Английска версия
                ├── readme.de.md       # Немска версия
                ├── guide.md           # Ръководство
                ├── guide.bg.md        # Ръководство (BG)
                ├── help.md            # Помощ
                └── help.bg.md         # Помощ (BG)

Dropdown менюта
===============

При отваряне на документацията, потребителят вижда три dropdown менюта:

1. **Език** (bg_BG, en_US, de_DE, и др.) - избор на език на документацията
2. **Файл** (readme.md, guide.md, help.md, и др.) - избор на документ
3. **Модул** - избор на модул, от който да се зареди документацията

След избор, натиснете бутона **"Зареди"** за да видите документа.

Конфигуриране на dropdown менюта
=================================

За да добавите повече опции в dropdown менютата, редактирайте ``markdown_popup.js``:

.. code-block:: javascript

    // Добавяне на нови езици
    const languages = [
        { value: 'bg_BG', label: 'Български (bg_BG)' },
        { value: 'en_US', label: 'English (en_US)' },
        { value: 'de_DE', label: 'Deutsch (de_DE)' },
        { value: 'fr_FR', label: 'Français (fr_FR)' },  // Нов език
    ];

    // Добавяне на нови файлове
    const files = [
        'readme.md',
        'guide.md',
        'help.md',
        'documentation.md',
        'tutorial.md',  // Нов файл
    ];

    // Добавяне на нови модули
    const modules = [
        'markdown_viewer_locale_dropdown',
        'l10n_bg_tax_admin',
        'custom_module',
        'your_new_module',  // Нов модул
    ];

Функция за търсене
==================

Вградената функция за търсене позволява на потребителите да намират бързо информация в документацията.
Търсенето работи в реално време и осветява намерените текстове с жълт фон.

Търсенето обхваща:

* Параграфи (``<p>``)
* Заглавия (``<h1>`` - ``<h6>``)
* Списъци (``<li>``)
* Код блокове (``<code>``, ``<pre>``)

Разлика с Markdown Viewer Locale
=================================

.. list-table::
   :header-rows: 1

   * - Функция
     - Markdown Viewer Locale
     - Markdown Viewer Locale Dropdown
   * - Автоматично зареждане по език
     - ✓
     - ✓
   * - Избор на език
     - ✗
     - ✓
   * - Избор на документ
     - ✗
     - ✓
   * - Избор на модул
     - ✗
     - ✓
   * - Търсене
     - ✓
     - ✓
   * - Syntax highlighting
     - ✓
     - ✓

Изисквания
==========

* Odoo 16.0+
* Bootstrap 5
* Библиотека marked.js (включена)
* Библиотека highlight.js (включена)

Конфигурация
============

Не се изисква допълнителна конфигурация. Модулът работи веднага след инсталиране.

Бъг тракер
==========

Ако откриете проблеми, моля докладвайте ги в GitHub Issues.

Автори
======

* Вашата компания/име

Съдържание
==========

* ``static/lib/marked.min.js``: Markdown parser
* ``static/lib/highlight.min.js``: Syntax highlighting за код
* ``static/src/js/markdown_popup.js``: JavaScript компонент с dropdown функционалност
* ``static/src/css/markdown_popup.css``: Стилове
* ``static/src/xml/markdown_popup.xml``: OWL шаблон с dropdown менюта
* ``views/markdown_snippet.xml``: Snippet за добавяне в изгледи

Лиценз
======

LGPL-3

Одобрения
=========

Този модул използва следните библиотеки:

* `marked.js <https://marked.js.org/>`_ - MIT License
* `highlight.js <https://highlightjs.org/>`_ - BSD License
