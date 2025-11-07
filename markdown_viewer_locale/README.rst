
=========================
Markdown Viewer Locale
=========================

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

|badge1|

Преглед на локализирани Markdown файлове въз основа на езика на потребителя.

**Основни функции:**

* Автоматично зареждане на Markdown файлове според езика на потребителя
* Fallback към основния файл, ако липсва локализация
* Интегрирана функция за търсене в съдържанието
* Syntax highlighting за code блокове
* Модален прозорец на цял екран

Използване
==========

Метод 1: Snippet шаблон
-----------------------

След инсталиране на модула, добавете snippet-а във вашите изгледи:

.. code-block:: xml

    <t t-call="markdown_viewer_locale.markdown_snippet">
        <t t-set="md_file" t-value="'readme.md'"/>
        <t t-set="md_module" t-value="'your_module_name'"/>
    </t>

Метод 2: Директен линк
----------------------

Използвайте директно линк с data атрибути:

.. code-block:: xml

    <a href="#" class="o_show_markdown"
       data-md-file="readme.md"
       data-md-module="your_module_name"
       title="Виж документацията">
        <i class="fa fa-book fa-lg"></i>
    </a>

Метод 3: Икона във формуляр (препоръчително)
--------------------------------------------

За да добавите икона за документация във формуляр на Odoo:

.. code-block:: xml

    <odoo>
        <record id="view_move_form_inherit_md_icon" model="ir.ui.view">
            <field name="name">account.move.form.md.icon</field>
            <field name="model">account.move</field>
            <field name="inherit_id" ref="account.view_move_form"/>
            <field name="arch" type="xml">
                <!-- Вмъкваме икона вътре във формата -->
                <xpath expr="//form" position="inside">
                    <div class="o_md_icon_container">
                        <i class="fa fa-book o_show_markdown"
                           title="Документация"
                           data-md-file="l10n_bg_tax_admin_documentation.md"
                           data-md-module="l10n_bg_tax_admin"></i>
                    </div>
                </xpath>
            </field>
        </record>
    </odoo>

**Важно:** Добавете CSS стилове за позициониране на иконата:

.. code-block:: css

    .o_md_icon_container {
        position: absolute;
        top: 10px;
        right: 20px;
        z-index: 1000;
    }

    .o_md_icon_container .fa-book {
        font-size: 24px;
        color: #4caf50;
        cursor: pointer;
        transition: color 0.3s;
    }

    .o_md_icon_container .fa-book:hover {
        color: #45a049;
    }

Структура на файловете
=======================

Създайте Markdown файлове в следната структура:

.. code-block:: text

    your_module/
    └── static/
        └── src/
            └── md/
                ├── readme.md                              # Основен файл (fallback)
                ├── readme.bg.md                           # Българска версия
                ├── readme.en.md                           # Английска версия
                ├── l10n_bg_tax_admin_documentation.md     # Документация (fallback)
                ├── l10n_bg_tax_admin_documentation.bg.md  # Документация (BG)
                └── l10n_bg_tax_admin_documentation.en.md  # Документация (EN)

Модулът автоматично ще зареди файла според езика на потребителя (напр. за ``bg_BG`` ще търси ``l10n_bg_tax_admin_documentation.bg.md``).

Проверка на работоспособността
================================

**Стъпка 1: Проверка на файловете**

Уверете се, че Markdown файловете са на правилното място:

.. code-block:: bash

    # Проверете структурата на файловете
    ls -la your_module/static/src/md/

Трябва да видите файловете:

.. code-block:: text

    l10n_bg_tax_admin_documentation.md
    l10n_bg_tax_admin_documentation.bg.md
    l10n_bg_tax_admin_documentation.en.md

**Стъпка 2: Рестартирайте Odoo**

.. code-block:: bash

    # Рестартирайте сървъра и обновете модула
    odoo-bin -u markdown_viewer_locale,l10n_bg_tax_admin

**Стъпка 3: Изчистете кеша на браузъра**

Натиснете ``Ctrl+Shift+R`` (или ``Cmd+Shift+R`` на Mac) за да изчистите кеша.

**Стъпка 4: Отворете формуляра**

Отворете формуляр на ``account.move`` и потърсете иконата 📚 в горния десен ъгъл.

**Стъпка 5: Тестване**

1. Кликнете на иконата 📚
2. Трябва да се отвори модален прозорец с документацията
3. Проверете дали се зарежда правилният език (според ``bg_BG``, ``en_US``, и т.н.)
4. Тествайте функцията за търсене

**Стъпка 6: Проверка в конзолата на браузъра**

Отворете Developer Tools (F12) и проверете за грешки:

.. code-block:: javascript

    // Трябва да видите зареждане на файловете
    // Ако има грешка 404, проверете пътищата

**Отстраняване на проблеми**

Ако иконата не се показва:

1. **Проверете CSS стиловете** - Добавете ``.o_md_icon_container`` стилове в CSS файла
2. **Проверете XPath** - Уверете се, че ``//form`` съществува в изгледа
3. **Проверете класа** - Трябва да е ``.o_show_markdown``, не ``.o_show_markdown_dropdown``
4. **Проверете assets** - Уверете се, че JS и CSS файловете са добавени в манифеста

Ако модалът не се отваря:

1. **Проверете конзолата** - Потърсете JavaScript грешки
2. **Проверете пътя** - Уверете се, че ``data-md-module`` и ``data-md-file`` са правилни
3. **Проверете файловете** - Уверете се, че Markdown файловете съществуват

Ако се вижда грешка 404:

.. code-block:: text

    GET http://localhost:8069/l10n_bg_tax_admin/static/src/md/l10n_bg_tax_admin_documentation.bg.md 404

Това означава, че:

* Файлът липсва на указаното място
* Името на модула е грешно в ``data-md-module``
* Името на файла е грешно в ``data-md-file``

Поддържани езици
================

Модулът поддържа всички езици, като използва първата част от locale кода:

* ``bg_BG`` → ``documentation.bg.md``
* ``en_US`` → ``documentation.en.md``
* ``de_DE`` → ``documentation.de.md``
* ``fr_FR`` → ``documentation.fr.md``
* и т.н.

Функция за търсене
==================

Вградената функция за търсене позволява на потребителите да намират бързо информация в документацията.
Намерените текстове се осветяват с жълт фон.

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
* ``static/src/js/markdown_popup.js``: JavaScript компонент
* ``static/src/css/markdown_popup.css``: Стилове
* ``static/src/xml/markdown_popup.xml``: OWL шаблон
* ``views/markdown_snippet.xml``: Snippet за добавяне в изгледи

Примерна документация
=====================

Създайте ``l10n_bg_tax_admin_documentation.bg.md``:

.. code-block:: markdown

    # Документация за НАП администрация

    ## Въведение

    Този модул предоставя функционалност за работа с НАП.

    ## Функции

    * Генериране на XML файлове
    * Валидация на данни
    * Изпращане към НАП

    ## Примерен код

    ```python
    def generate_xml(self):
        # Генериране на XML
        return xml_content
    ```

Лиценз
======

LGPL-3

Одобрения
=========

Този модул използва следните библиотеки:

* `marked.js <https://marked.js.org/>`_ - MIT License
* `highlight.js <https://highlightjs.org/>`_ - BSD License
