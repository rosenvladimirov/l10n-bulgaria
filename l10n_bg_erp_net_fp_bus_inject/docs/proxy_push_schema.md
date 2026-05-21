# Proxy push JSON convention

> Канонична схема за всички live event push-ове от хардуерното прокси
> (Odoo.ErpNet.FP) към Odoo през `bus.bus`. Този документ е stable
> contract — нови event-и просто разширяват type registry-та без да
> чупят envelope-а.

## Envelope

```jsonc
{
  "v": 1,                          // schema version (int)
  "type": "plate.detected",        // <noun>.<verb> или <noun>.<state>
  "source": {
    "proxy": "rosen-laptop",       // proxy.name (от registry)
    "device": "camera.front",      // device-id вътре в проксито
    "device_kind": "camera"        // camera | access | reader | mqtt
                                   //         | biometric | controller
  },
  "ts": "2026-05-21T11:55:32.401Z",// ISO-8601 UTC; server-stamped
  "id": "a3f7…uuid",                // UUID per event (dedup + tracing)
  "data": {                         // type-specific payload (free form)
    "plate": "СК1234БГ",
    "confidence": 0.94
  }
}
```

### Полета които ПРОКСИТО подава

- `v` — почти винаги `1` (вижте „Versioning" по-долу)
- `type` — задължително (виж registry-та)
- `source.proxy` — задължително; служи и за HMAC routing
- `source.device` / `source.device_kind` — препоръчително (frontend-ът
  филтрира по тях)
- `data` — задължително (може и `{}`)

### Полета които СЪРВЪРЪТ попълва (proxy ги пропуска)

- `ts` — Odoo controller-ът stamp-ва UTC time
- `id` — Odoo controller-ът генерира UUID4 ако не е подаден

## Channel

Един канал за всички proxy push-ове:

```
erpnet_fp_proxy_events
```

Filtering е винаги client-side (frontend Owl service диспечира по
`type`, `source.proxy`, `source.device`).

## Event type registry

| Type | Когато се пуска | `data` минимум |
|------|-----------------|----------------|
| `plate.detected` | LPR camera прочете номер | `plate`, `confidence` |
| `plate.injected` | Manual test plate за дебъг | `plate`, `source:"manual"` |
| `card.read` | RFID/keypad reader scan | `card_id`, `reader_id` |
| `door.opened` | Controller actuates output | `door_id`, `by` |
| `door.denied` | Reader → policy → reject | `reason`, `card_id?` |
| `door.sensor` | Door contact state changed | `state:"open"\|"closed"` |
| `button.pressed` | Exit / REX button | `button_id` |
| `barrier.changed` | Gate motor state | `state:"moving"\|"stopped"\|"fault"` |
| `controller.heartbeat` | Per-Polimex pulse | `seq`, `status_word` |
| `controller.unreachable` | Missed heartbeats threshold | `last_seen`, `missed_count` |
| `mqtt.message` | MQTT subscriber gets payload | `topic`, `raw_payload` |
| `biometric.match` | Face-auth recognized subject | `subject_id`, `score` |

## Naming convention за нови types

- lowercase, точка separator: `<noun>.<verb>` или `<noun>.<state>`
- noun = device kind или domain concept (NOT vendor name — „polimex"
  не е валидно noun)
- verb / state = action или итог
- Винаги конкретно — `event` / `data` / `update` са забранени като noun
- За generic broadcasts на ниво proxy използвай noun `proxy.`,
  например `proxy.online` / `proxy.unreachable`

## Versioning

Schema version (`v`) се bump-ва САМО при:
- Преименуване или премахване на поле в envelope
- Преструктуриране на `source` обекта
- Промяна в семантиката на `id` или `ts`

НЕ bump при:
- Добавяне на нов `type`
- Добавяне на нови опционални полета в `data.*`
- Добавяне на нов device_kind

Backend поддържа множество v-та едновременно за поне 6 месеца след
въвеждане на нова версия.

## Auth (HMAC)

Proxy подписва тялото с HMAC-SHA256 ключ = неговия `registry_secret`:

```
X-Bus-Inject-Signature: <hex(hmac_sha256(body, secret))>
X-Bus-Inject-Proxy: <proxy_name>
```

Same scheme as the Fleet heartbeat — нямa нов token за управление.

## Authoritative vs live

Това е САМО live signal — без DB запис. Ако event-ът трябва да се
запише (attendance, audit log), проксито трябва ОТДЕЛНО да POST-не
към съответния HTTP endpoint:
- `/lpr_gateway` за plate audit
- `/access/event` за door audit
- (нови ще се добавят при нужда)

Bus inject и HTTP-with-record са допълнителни, не алтернативни.
