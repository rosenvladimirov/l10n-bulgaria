# Claude Artifacts to Blog (Odoo Snippets)

Collects Claude artifacts and turns them into blog posts built from **native Odoo
website snippets** — not a styled HTML dump inside one text block.

## Why

An artifact is a self-contained HTML page: it carries its own CSS, its own
layout, and often its own diagrams. Pasting it into `blog.post.content` gives a
post that looks right and cannot be edited: the website editor does not
recognise a single block in it, and the site theme has no say over the result.

This module takes the artifact apart and puts it back together with the snippets
Odoo already knows — `s_title`, `s_text_block`, `s_alert`, `s_blockquote`,
`s_big_number`, `s_accordion`, `s_table_of_content`, `s_hr`. The article is then
edited like any other page.

## The path

```
collected  ->  parsed  ->  built  ->  published
   raw        blocks     snippets    blog draft
```

Every step leaves a visible result. The blocks are real records: before anything
reaches the blog you can see what was recognised, which snippet each block maps
to, and switch off the ones you do not want.

## Two ways in

**From a Claude session** — call the `collect` method over RPC/MCP:

```python
models.execute_kw(db, uid, key, "claude.artifact", "collect", [{
    "title": "Warehouse figures",
    "content": open("artifact.html").read(),
    "format": "html",              # or "markdown"
    "url": "https://claude.ai/...",  # kept for the record
    "session": "sess-2026-09-11",
    "blog_id": 3,
    "build": True,
}])
```

It returns `{id, name, state, reused, blocks, kinds, blog_post_id, url}`.
Re-sending the same content returns the existing artifact instead of a duplicate
— the checksum is the identity.

**By hand** — *Website → Configuration → Claude Artifacts → Import Artifact*:
upload the `.html`/`.md` file or paste the source.

## What gets recognised

| In the artifact | Becomes | Rendered as |
|---|---|---|
| `<h2>` | section heading | `s_title` + table-of-content anchor |
| `<h3>`…`<h6>` | in-section heading | inside the current `s_text_block` |
| `<p>`, `<ul>`, `<ol>` | text | `s_text_block` |
| `<p class="eyebrow">` | kicker | feeds the subtitle, not the body |
| `<p class="standfirst">` | lead paragraph | `s_text_block` with `.lead` |
| `<pre><code>` | code | `<pre>` with the module's own styling |
| `<table>` | table | `s_text_block` + `.table-responsive` |
| `<blockquote>` | quote | `s_blockquote` |
| `🚨 ⚠️ ✅ ℹ️` or `.alert`/`.warning` | callout | `s_alert`, level from the marker |
| `<dl class="stat">` | figures board | columns with the numbers |
| `.kpi` with a number | single figure | `s_big_number` |
| `<details><summary>` | accordion | `s_accordion` |
| `<svg>` | diagram | inline, with the artifact colours preserved |
| `<figure><figcaption>` | figure | image or diagram with its caption |

The mapping lives in `claude.snippet.rule` records, not in code — snippets change
between Odoo series, and "a table goes into a scroller" is a decision, not an
algorithm. Edit it from *Snippet Rules* (system administrator).

## What never happens

- **Nothing reaches the site on its own.** `blog.post` is always created with
  `website_published = False`.
- **The artifact CSS does not leak.** `<script>` and `<style>` are dropped. The
  only exception is diagram styling, which is inlined onto the SVG elements
  themselves — a `<style>` inside an inline SVG is *not* scoped to it and would
  repaint the whole page.
- **No LLM is involved.** The parser is deterministic: the structure of the
  artifact carries the meaning.

## Checking the result

The **Check Coverage** button compares the words of the artifact with the words
of the built article and writes the number in the chatter. Chasing snippets can
quietly eat a whole table; the number is measured on the *result*, not on the
blocks.

## Table of content

Articles with four or more level-2 headings get the `s_table_of_content` wrapper
with its sticky navigation. Set it to *Always* or *Never* per artifact. The
anchors follow the `table_of_content_heading_N_M` convention — the website
builder recognises no other form.

## Requirements

Odoo 19.0, `website_blog`, `lxml`. The user needs *Website / Editor and
Designer* to create blog posts.
