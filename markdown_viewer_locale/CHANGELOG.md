# Changelog

All notable changes to the markdown_viewer_locale module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.3.0.8] - 2026-04-30

### Changed
- Disabled `markdown_popup.js` asset entry in `__manifest__.py`. The `patch(FormController.prototype, ...)` call no longer runs. Module is now effectively a no-op — only `markdown_registry.js` remains active (kept so that dependent modules' imports of `markdownRegistry` resolve).

### Why
- 18.0.3.0.7 (XML extension disabled) did not fix Knowledge Share. With XML and now JS patch both disabled, `markdown_viewer_locale` cannot influence Owl rendering. If the Share `VList.mount` error persists at this version, the root cause is **definitively elsewhere** — not in this module — and the original handoff diagnosis was incorrect.

### How to apply
- Deploy 18.0.3.0.8 to teo-engineering, click Share on a Knowledge article.
  - **Works** → JS patch (despite never being called during render) somehow caused the issue. Investigate further.
  - **Still broken** → bug is outside `markdown_viewer_locale`. Stop iterating on this module. Likely candidates: another patched module on prod (zombie or active), stale asset attachment, or a Knowledge-specific issue. Recommended next move: enable `--dev=qweb,xml,assets` on prod to get unminified Owl traceback with component name.

## [18.0.3.0.7] - 2026-04-30

### Changed
- Temporarily disabled the XML asset entry for `static/src/xml/form_controller.xml` in `__manifest__.py`. Templates `MarkdownControlPanel`, `Markdown.FormView`, `Markdown.Icon` no longer extend `web.ControlPanel` / `web.FormView`.

### Why
- 18.0.3.0.6 (welcome registration commented out) did not fix Knowledge Share — confirms registration is not the cause. Next isolation step: remove the template inheritance entirely. JS patch on `FormController.prototype` stays — its methods are never called during render, so they cannot break Owl unless there is an unrelated interaction.

### How to apply
- Deploy 18.0.3.0.7 to teo-engineering, click Share on a Knowledge article.
  - **Works** → template inheritance (XML) is the cause; need a non-extending mechanism for the button.
  - **Still broken** → next step is to also disable the JS patch (comment out the `patch()` call in `markdown_popup.js`).
- Markdown popup button will be missing in the form view while this test is active — expected.

## [18.0.3.0.6] - 2026-04-30

### Changed
- Temporarily commented out the `welcome` registration in `markdown_registry.js` (was registered with `models=null` = "all models").

### Why
- Diagnostic step for Knowledge Share `VList.mount` breakage on teo-engineering prod. After 18.0.3.0.5 bump didn't help, browser logs show the Owl error firing right after `LogiKal Markdown документации регистрирани: 11` — i.e. after the registration chain completes. Hypothesis: the `models=null` welcome entry combined with the 11 LogiKal docs participates in something that disrupts FormView rendering. Removing welcome alone is the smallest revertible test.

### How to apply
- Deploy 18.0.3.0.6 to teo-engineering, click Share on a Knowledge article.
  - **Works** → root cause confirmed; next step is to find a non-breaking registration mechanism.
  - **Still broken** → uncomment welcome, move on to disabling the XML extension instead.

## [18.0.3.0.5] - 2026-04-30

### Changed
- `marked.min.js` and `highlight.min.js` are now lazy-loaded (via `loadJS`) on first popup open instead of being bundled in `web.assets_backend`. Removes UMD/global pollution from every backend page load.
- Removed `setup()` override from `FormController.prototype` patch — only logged a debug string and unnecessarily intercepted the form lifecycle.
- Stripped all `console.log` debug statements from `markdown_popup.js` and `markdown_registry.js` (kept `console.error` for actual failures).

### Why
- Suspected interaction with the Knowledge **Share** popover (Owl `VToggler.mount` error). Reducing the patch surface narrows the diagnostic and removes legitimate code-quality concerns regardless of root cause.

## [18.0.3.0.4] - 2026-03-01

### Added
- Initial changelog entry
