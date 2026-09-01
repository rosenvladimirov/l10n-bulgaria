# Stock — предпазител при липсващ MTO маршрут

> Изтрит маршрут „Replenish on Order (MTO)" не бива да чупи формата на склада
> с `TypeError: 'NoneType' object is not subscriptable`.

**Модул:** `stock_mto_route_missing_fix` | **Версия:** 19.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** Inventory

## Описание

`StockWarehouse._get_global_route_rules_values()` нарочно изхвърля правило,
чийто маршрут е изчезнал:

```python
# `route_id` might be `False` if the user has deleted it, in such case we
# should simply ignore the rule
return {k: v for k, v in vals.items() if v.get('create_values', {}).get('route_id', True) and ...}
```

Два call site-а обаче индексират изхвърления ключ без проверка:

```python
mto_vals = supplier_wh._get_global_route_rules_values().get('mto_pull_id')
values = mto_vals['create_values']
```

| # | Метод | Кога се стига дотам |
|---|---|---|
| 1 | `create_resupply_routes()` | склад-доставчик с доставка в 1 стъпка (`ship_only`) се добавя в **Resupply From** |
| 2 | `_check_delivery_resupply()` | сменят се стъпките на доставка на склад, който презарежда друг |

Ако глобалният маршрут `stock.route_warehouse0_mto` е изтрит (и записът, и
външният идентификатор), и двата вдигат `TypeError` и складът вече не може да
се запише. Проверено — дефектът стои в 18.0, 19.0 и 20.0.

## Какво прави

Модулът **не** преписва двата метода — телата им се различават между версиите
на Odoo и копие би замразило поведението на една от тях (`create_resupply_routes`
например подава `propagate_warehouse_id` в 18.0, а в 19.0 — не). Вместо
това ги обвива с контекстен флаг, жив само докато тече самият вик, и под този
флаг:

- `_get_global_route_rules_values()` връща изхвърления `mto_pull_id` като празна
  обвивка, за да успее безусловното индексиране;
- `stock.rule.create()` отхвърля стойности без `route_id` — а това е точно и
  единствено MTO правилото, което няма къде да се закачи.

Резултатът е поведението, което коментарът в ядрото обещава: MTO правилото се
пропуска, inter-warehouse маршрутът и pull правилата му се създават нормално, а
в лога влиза предупреждение с името на липсващия външен идентификатор.

Когато MTO маршрутът съществува, модулът е **no-op** — нищо не се връща обратно
в речника и нищо не се отхвърля при create.

## Истинското лечение

Предпазителят държи системата на крака, но не възстановява маршрута. Проверка:

```sql
SELECT id, name->>'en_US' AS name_en, active, company_id FROM stock_route ORDER BY id;
SELECT * FROM ir_model_data WHERE module='stock' AND name='route_warehouse0_mto';
```

- **Няма такъв ред** → `odoo -d <db> -u stock --stop-after-init` пресъздава
  записа (той е под `noupdate="1"`, което спира презаписа, но не и създаването
  на липсващ външен идентификатор).
- **Маршрутът съществува, но без външен идентификатор** (преименуван) → не
  прави `-u stock`, ще получиш дубликат; върни само реда в `ir_model_data`.

Маршрутът е `active=False` по подразбиране в 19.0 — в UI се вижда само с филтър
Archived и при включени Multi-Step Routes.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `stock` | — |

## Тестове

`odoo -d <db> -i stock_mto_route_missing_fix --test-enable --stop-after-init`

Двата теста трият MTO маршрута и минават през двата call site-а.

## Съвместимост

Кодът не зависи от телата на методите, затова същият модул върви и на 18.0, и на
20.0 — сменя се само версията в манифеста.
