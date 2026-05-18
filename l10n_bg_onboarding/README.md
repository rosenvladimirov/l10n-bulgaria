# Bulgarian Localization Onboarding (`l10n_bg_onboarding`)

A distinctive, full-screen, narrative onboarding experience that runs
the Bulgarian localization step-by-step installation on **first login**
to a freshly created database.

- **Visual direction:** Folk-Modernist Editorial — *Ink & Rose*. Dark
  ink canvas, parchment type, Bulgarian-rose + Thracian-gold accents,
  animated **cross-stitch (шевица)** geometry, editorial display type,
  orchestrated phase transitions, finale burst.
- **Animations:** Lottie per chapter when the player + JSON assets are
  present; otherwise an elegant animated-SVG cross-stitch motif
  (graceful fallback — beautiful out of the box, Lottie is a drop-in
  enhancement). See `static/lib/lottie/PLACEHOLDER.md`.
- **Augment, not replace:** the in-Settings modal stepper stays for
  re-runs; this is the first-login experience only. Both reuse the
  exact same engine (`l10n.bg.vertical` / `.step` / `.wizard`) — **no
  business logic duplicated**; every action goes through the existing
  backend methods via ORM.

## How it triggers

- `auto_install=['l10n_bg_config']` → on a Bulgarian database it
  installs automatically (chain: BG DB → `l10n_bg` → `l10n_bg_config`
  → this).
- An `ir.actions.todo` (sequence 1) opens the full-screen client
  action `l10n_bg_onboarding.app` on first admin login, before the
  plain modal-stepper todo of `l10n_bg_db_installer`.

## Architecture

| File | Role |
|------|------|
| `static/src/onboarding/onboarding_action.js` | OWL client action; state machine (hero → chapters → finale); ORM wiring |
| `static/src/onboarding/onboarding_action.xml` | OWL/QWeb templates |
| `static/src/onboarding/onboarding.scss` | the Ink & Rose aesthetic |
| `static/src/onboarding/scene_engine.js` | Lottie loader + SVG cross-stitch fallback |
| `static/src/onboarding/chapters.js` | per-vertical narrative copy/motif map (EN) |
| `data/onboarding_data.xml` | `ir.actions.client` + `ir.actions.todo` |

## TODO / dev-verify (19.0)

- `ir.actions.todo` auto-presentation on first admin login (v17+ config
  chain is less used — confirm it fires; fallback: admin Home Action).
- De-dup with `l10n_bg_db_installer`'s modal-stepper todo (this one is
  sequence 1; confirm only one runs / the modal one is skipped once
  onboarding completes).
- OWL render on a real 19.0 instance (client action `target=fullscreen`,
  scene mount/unmount, ORM calls to step/wizard methods).
- Optional: vendor `lottie-web.min.js` + chapter JSONs.
- 18.0 port after 19.0 dev-verify.
