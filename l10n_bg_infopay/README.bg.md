# InfoPay Integration (l10n_bg_infopay) — БГ

> **Текуща версия:** 18.0.4.1.0 · **Лиценз:** LGPL-3 · **Статус:** ядро
> на InfoPay подсистемата.  Виж `CHANGELOG.md` за пълната история на
> версиите.

`l10n_bg_infopay` е **ядрото с настройки + общи помощници** за
интеграцията с Borica InfoPay PSD2 API в Odoo 18.  Сам по себе си
покрива пълния workflow за една фирма (синхронизация на извлечения,
издаване на фактури, единични и bulk платежни нареждания, опресня-
ване на статус) върху journals на активната фирма.  Интеграция с
външни framework-и (`account.payment.order` от OCA,
`account.batch.payment` от Enterprise, OdooFin синхронизация) става
през малки **bridge модули**, които зависят от това ядро.

## Структура на модулите

```
l10n_bg_infopay/                      ← ТОЗИ МОДУЛ (ядро)
├── infopay.provider                    суров HTTP клиент (session,
│                                       accounts, transactions, payments)
├── res.company                         пълномощия (user + admin token)
├── account.journal                     IBAN-конфигурация + sync
├── account.payment                     single + bulk submit + polling
├── account.move                        издаване на InfoPay фактура
├── l10n.bg.infopay.statement.mixin     абстрактен миксин за bridges
└── l10n.bg.infopay.payment.mixin       абстрактен миксин за bridges

l10n_bg_infopay_oca_statement       ← bridge: OCA online.bank.statement.provider
l10n_bg_infopay_oca_payment         ← bridge: OCA account.payment.order
l10n_bg_infopay_ee_statement        ← bridge: EE  account.online.account
l10n_bg_infopay_ee_payment          ← bridge: EE  account.batch.payment
l10n_bg_infopay_ui                  ← общо: wallet-unlock + бутони
```

## Какво осигурява

* **Шифрирани пълномощия** — user wallet (защитен с парола през
  `l10n_bg_bank_wallet`) за write операции + admin Fernet-шифриран
  token за cron read операции.  Двойнокаталогов модел за да не се
  пази потребителска парола в крон.
* **Синхронизация на банкови извлечения** —
  `journal._l10n_bg_infopay_pull_transactions(date_from, date_to)`
  тегли + дедупликира, готови за съпоставяне.
* **Единични плащания** — BGN вътрешни, SEPA EUR, BGN бюджет (НАП).
  Връща `paymentId` + `scaRedirect` URL за SCA.
* **Bulk плащания** — 2..250 елемента през bulk endpoint-ите.
* **Опресняване на статус** — single + bulk `/payments/{id}/status`.
* **Издаване на фактура** — `/api/invoices` за InfoPay платежни
  линкове (това **НЕ** е регулираната `e-faktura.bg`).

## Какво е НОВО в 18.0.4.x

* **18.0.4.1.0** — добавени три нови `account.payment.method` записа
  (`l10n_bg_infopay_domestic_bgn`, `_sepa_eur`, `_budget_bgn`),
  използвани от OCA + EE payment bridge-овете.
* **18.0.4.0.0** — **breaking** rename: всяко поле, което този модул
  добавя на публичен Odoo модел, вече има префикс `l10n_bg_`
  (`infopay_unique_id` → `l10n_bg_infopay_unique_id` и т.н.).
  Pre-migration скрипт прави осемте `ALTER TABLE RENAME COLUMN`
  идемпотентно; съществуващите данни се запазват.

## Инсталация

```bash
pip install requests cryptography
git clone <l10n-bulgaria>
git clone <l10n-bulgaria-expert>   # опционално: OCA bridge-овете
git clone <l10n-bulgaria-ee>       # опционално: EE bridge-овете
```

`-i l10n_bg_infopay` инсталира само ядрото; bridge-овете са
`auto_install=True`, така че се вдигат автоматично щом host
framework-ите (`account_payment_order`, `account_online_synchronization`,
`account_batch_payment`) са налични.

## Настройка

1. Отвори **Settings → Companies → InfoPay**.
2. Постави `Unique ID`-то от Borica регистрацията.
3. Въведи **user token** в wallet-а (защитен с парола).
4. Въведи **admin token** — Fernet-шифрира се в `ir.config_parameter`
   за неконтролирана крон употреба.
5. На всеки банков journal задай **InfoPay account UUID**, който
   съответства на IBAN-а на journal-а.  Discovery wizard
   (`l10n_bg_infopay_ui` модул) може да попълни UUID-а автоматично.

## Лиценз

LGPL-3 — виж https://www.gnu.org/licenses/lgpl

## Автор

Розен Владимиров, Odoo Community Association (OCA).
