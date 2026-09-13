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
      <h2><span class="num">01</span>Какво беше измерено</h2>
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

# Втората фикстура носи СТРУКТУРИТЕ, които парсерът разтваряше до абзаци
# (ADR-0004). Формите са свалени от истинските артефакти, съдържанието е
# измислено:
#   * табло <div class="mm"><span>етикет</span><b>стойност</b></div>
#   * табло <div class="fig bad"><span class="n">24</span><span>…</span></div>
#   * число с обяснение <div class="deadline"><span class="num">30</span><p/></div>
#   * глава на секция <div class="sec-head"><div class="sec-num">02</div>
#     <h2/><p class="sec-sub"/></div>
#   * карти <div class="axis"><div class="an"/><span class="scale"/><p/></div>
#   * карта със значка в заглавието <h4><span class="pill ok"/>…</h4>
#   * въпроси <div class="q"><div><b>…</b><span>…</span></div></div>
#   * стъпки <div class="step"><div class="sn">0</div><h4/><p class="cost"/>
#     <div class="body"/></div>
#   * бележки note key / note trap, чипове, span.m, поредни <details>
#   * таблица с colspan, два заглавни реда и числови колони
RICH_ARTIFACT_HTML = """<!DOCTYPE html>
<html lang="bg">
<head><meta charset="utf-8"/><title>Одитът на склада</title></head>
<body>
<div class="wrap">
  <header class="mast">
    <p class="eyebrow">одит · 12.09.2026</p>
    <h1>Одитът на склада</h1>
    <p class="dek">Какво се мени между двете версии и колко струва преходът.</p>
    <div class="mast-meta">
      <div class="mm"><span>версия днес</span><b>19.4-alpha</b></div>
      <div class="mm"><span>измерени модула</span><b>296 от ~662</b></div>
      <div class="mm"><span>чупещи промени</span><b>50</b></div>
    </div>
    <div class="deadline"><span class="num">30</span><p><strong>дни до
      замразяването</strong>, след което API-то спира да мърда.</p></div>
  </header>
  <section>
    <div class="sec-head"><div class="sec-num">01</div><h2>Присъдите по осите</h2>
      <p class="sec-sub">Всяка ос с оценка и едно изречение защо.</p></div>
    <div class="figures">
      <div class="fig bad"><span class="n">24</span><span class="l">души с достъп</span></div>
      <div class="fig good"><span class="n">0</span><span class="l">с права admin</span></div>
    </div>
    <div class="axes">
      <div class="axis"><div class="an">Сигурност</div><span class="scale s-rw">пренаписване</span>
        <p>Два модела стават един: <code>ir.model.access</code> и <span class="m">ir.rule</span>.</p></div>
      <div class="axis"><div class="an">Склад</div><span class="scale">еволюция</span>
        <p>Скелетът остава, сменя се <span class="chip ok">uom_id</span>.</p></div>
    </div>
    <div class="note key"><b>Изводът:</b> това не е следваща версия, а друга платформа.</div>
    <div class="note trap"><b>Капанът:</b> търсенето е по равенство, не по „става ли".</div>
  </section>
  <section>
    <div class="sec-head"><div class="sec-num">02</div><h2>Поправеното</h2></div>
    <div class="cards">
      <div class="card ok"><h4><span class="pill ok">затворено</span> Резисторите влязоха</h4>
        <p>Нов ред в спецификацията.</p><div class="proof">R003 R016 R017</div></div>
      <div class="card ok"><h4><span class="pill ok">затворено</span> Количеството стана 6</h4>
        <p>Сверено срещу схемата.</p></div>
    </div>
    <div class="qs">
      <div class="q"><div><b>Обхват</b><span>Влизат ли модулите извън анализа в новата версия?</span></div></div>
      <div class="q"><div><b>Срок</b><span>Кога тръгва изравняването на линията?</span></div></div>
    </div>
  </section>
  <section>
    <h2>Ред на действие</h2>
    <div class="steps">
      <div class="step"><div class="sn">0</div><h4>Пресен еталон</h4><p class="cost cheap">евтино · часове</p>
        <div class="body"><p>Изтегляне на четирите дървета.</p><p><strong>Защо:</strong> еталонът е стар.</p></div></div>
      <div class="step"><div class="sn">1</div><h4>Решение по обхвата</h4><p class="cost">решение</p>
        <div class="body"><p>Влизат ли модулите извън анализа.</p></div></div>
    </div>
    <details><summary>Първи въпрос</summary><p>Първи отговор.</p></details>
    <details><summary>Втори въпрос</summary><p>Втори отговор.</p></details>
    <details><summary>Трети въпрос</summary><p>Трети отговор.</p></details>
    <table>
      <thead>
        <tr><th>ос</th><th colspan="2">попадения</th></tr>
        <tr><th>модел</th><th class="num">CE</th><th class="num">EE</th></tr>
      </thead>
      <tbody><tr><td class="m">ir.rule</td><td class="num">237</td><td class="num">1 094</td></tr></tbody>
    </table>
  </section>
</div>
</body>
</html>
"""
