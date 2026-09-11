# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Фикстура, която възпроизвежда СТРУКТУРАТА на истинските артефакти.

Съдържанието е измислено нарочно — истинските артефакти са работни документи.
Структурите обаче са свалени едно към едно от тях, включително тези, които
парсерът изяждаше тихо:
  * <p class="eyebrow"> и <p class="standfirst"> около h1
  * <dl class="stat"><div><dt>етикет</dt><dd>число<small>бележка</small></dd></div>
  * <div class="kpi"><span>число</span><span>дълъг етикет</span><span>трети</span>
  * <figure><div><svg/></div><details><summary/><table/></details><figcaption/>
  * ограден код с language- клас
"""

ARTIFACT_HTML = """<!DOCTYPE html>
<html lang="bg">
<head>
  <meta charset="utf-8"/>
  <title>Разчетът на склада</title>
  <style>
    :root { --accent: #0E6B5E; --ink: #12201D; }
    body { font-family: serif; } .kpi { display: grid; }
    .chart .bar { fill: var(--accent); }
    .chart .lbl { fill: var(--ink); font-weight: 600; }
  </style>
</head>
<body>
  <div class="wrap">
    <section>
      <p class="eyebrow">технически разчет · 11.09.2026 · работен документ</p>
      <h1>Разчетът на склада</h1>
      <p class="standfirst">Кратък водещ абзац, който казва какво показва
         документът и защо числата в него значат нещо.</p>
      <dl class="stat">
        <div><dt>партиди</dt><dd>18<small>от 4 200 общо</small></dd></div>
        <div><dt>засегнати реда</dt><dd>935<small>и 496 премахнати</small></dd></div>
        <div><dt>период</dt><dd>5<small>седмици, 11.05–15.06</small></dd></div>
      </dl>
    </section>
    <section>
      <h2>Какво беше измерено</h2>
      <p>Първи абзац от раздела с <b>подчертана</b> дума и
         <a href="https://example.org/doc">препратка</a>.</p>
      <div class="kpi">
        <span>49</span>
        <span>партиди без движение</span>
        <span>от които 7 с изтекъл срок</span>
      </div>
      <h3>Подраздел</h3>
      <p>Абзац в подраздела.</p>
      <ul><li>първо наблюдение</li><li>второ наблюдение с <code>код</code></li></ul>
      <pre><code class="language-python">def total(lines):
    return sum(line.qty for line in lines)</code></pre>
      <p class="warning">🚨 Партида без срок минава като валидна — това е капан.</p>
      <blockquote><p>Числото брои носители, не съдържание.</p><cite>работна бележка</cite></blockquote>
    </section>
    <section>
      <h2>Таблицата на серията</h2>
      <table>
        <thead><tr><th>ден</th><th class="num">партиди</th><th class="num">редове</th></tr></thead>
        <tbody>
          <tr><td>15.08</td><td class="num">126</td><td class="num">1 094</td></tr>
          <tr><td>30.08</td><td class="num">914</td><td class="num">2 311</td></tr>
        </tbody>
      </table>
      <figure>
        <div class="chart"><svg viewBox="0 0 100 40" role="img" aria-label="Партиди по месеци">
          <rect class="bar" x="2" y="20" width="8" height="18"/>
          <text x="2" y="12" class="lbl">18 · юни</text>
          <text x="2" y="30" class="note">49 · август</text>
        </svg></div>
        <details>
          <summary>таблица на серията</summary>
          <div class="scroll"><table>
            <thead><tr><th>месец</th><th class="num">брой</th></tr></thead>
            <tbody><tr><td>юни</td><td class="num">18</td></tr>
                   <tr><td>август</td><td class="num">49</td></tr></tbody>
          </table></div>
        </details>
        <figcaption>Партиди без движение по месеци, 11.05 → 30.08.</figcaption>
      </figure>
      <hr/>
    </section>
    <section>
      <h2>Какво следва</h2>
      <p>Заключителен абзац.</p>
      <h2>Бележки</h2>
      <p>Източниците са в работната директория.</p>
    </section>
  </div>
  <script>console.log("това не бива да стига до блога");</script>
</body>
</html>
"""

ARTIFACT_MARKDOWN = """# Разчетът на склада

Кратък водещ абзац за документа.

## Какво беше измерено

Първи абзац с **подчертана** дума и `код` вътре.

- първо наблюдение
- второ наблюдение

```python
def total(lines):
    return sum(line.qty for line in lines)
```

| ден | партиди |
| --- | ------- |
| 15.08 | 126 |
| 30.08 | 914 |

> Числото брои носители, не съдържание.

---

## Какво следва

Заключителен абзац.
"""
