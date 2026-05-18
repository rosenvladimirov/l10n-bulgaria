# Lottie (optional, drop-in)

Place `lottie-web.min.js` here (the standalone bodymovin/lottie-web
player, ~250 KB) to enable Lottie-driven chapter animations:

    static/lib/lottie/lottie-web.min.js

Source: https://github.com/airbnb/lottie-web (dist/lottie.min.js),
LGPL-compatible MIT. Vendor it offline — do **not** rely on a CDN in
production.

Then drop chapter animation JSONs into:

    static/src/anim/v0.json … v12.json   (keyed by vertical code)

Without these files the onboarding still renders a polished animated
SVG cross-stitch motif per chapter (graceful fallback) — Lottie is an
enhancement, never a hard dependency.

⚠️ The repo `.gitignore` ships a Python `lib/` rule that silently
excludes `static/lib/*`. A `!l10n_bg_onboarding/static/lib/` negation
has been added; still commit vendored binaries with
`git add -f static/lib/lottie/lottie-web.min.js` and verify with
`git check-ignore`. (See memory: gitignore-lib-eats-static-lib.)
