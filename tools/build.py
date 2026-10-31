"""生成 ManimGX 站点的静态页面。

用法::

    python3 tools/build.py            # 用 src/snippets.json 里缓存的代码片段生成页面
    python3 tools/build.py --extract  # 先从素材目录重新摘取代码片段，再生成页面

代码片段都按行号从真实的 scene.py / 脚本里截取，页面上的行号就是源文件的行号。
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SOURCE_DIR = Path(os.environ.get("MANIMGX_SRC", "/mnt/d/ManimGX"))

MAIN_SITE = "https://goaltang.github.io/"
FILM = MAIN_SITE + "films/{id}.mp4"
COVER = MAIN_SITE + "covers/{id}.jpg"
SITE_URL = "https://goaltang.github.io/manimgx/"

# --------------------------------------------------------------------------- #
# 片段：从素材目录按行号摘取
# --------------------------------------------------------------------------- #
SNIPPETS = {
    "definite-integral": ("DefiniteIntegralArea_scene.py", [(57, 94)]),
    "tcp-handshake": ("02-tcp-handshake/scene.py", [(86, 116)]),
    "matrix-transform": ("01-matrix-transform/scene.py", [(178, 213)]),
    "pythagoras": ("03-pythagoras/scene.py", [(457, 469), (500, 519)]),
    "projectile": ("05-projectile/scene.py", [(532, 560)]),
    "roadster": ("07-roadster/scene_principle.py", [(106, 108), (613, 649)]),
    "dong-force": ("08-dong-joint/DongForceTransfer.srt", [(1, 51)]),
    "four-stroke": ("_transfer/grok-out/fs_run2.py", [(8, 18)]),
    # “怎么做的”页
    "how-scene": ("DefiniteIntegralArea_scene.py", [(12, 23)]),
    "how-config": ("03-pythagoras/scene.py", [(19, 20), (38, 40)]),
    "how-font": ("07-roadster/scene_principle.py", [(111, 137)]),
    "how-lru": ("04-lru/scene.py", [(192, 211), (228, 231)]),
    "how-captions": ("07-roadster/scene_principle.py", [(56, 60), (87, 108)]),
    "how-timings": ("07-roadster/scene_principle.py", [(591, 611)]),
    "how-mix": ("_transfer/grok-out/fs_run2.py", [(20, 33), (44, 47)]),
    "how-poster": ("_transfer/posters.sh", [(1, 8)]),
}

TRANSCRIPTS = {
    "roadster": ("07-roadster/narration_text.json", "json-list"),
    "dong-force": ("08-dong-joint/DongForceTransfer.srt", "srt"),
    "four-stroke": ("09-four-stroke/four-stroke_narration.srt", "srt"),
}


def extract() -> None:
    data: dict = {"snippets": {}, "transcripts": {}}
    for key, (rel, ranges) in SNIPPETS.items():
        lines = (SOURCE_DIR / rel).read_text(encoding="utf-8-sig").splitlines()
        blocks = []
        for start, end in ranges:
            end = min(end, len(lines))
            blocks.append({"start": start, "lines": lines[start - 1 : end]})
        data["snippets"][key] = {"file": rel, "blocks": blocks}
    for key, (rel, kind) in TRANSCRIPTS.items():
        text = (SOURCE_DIR / rel).read_text(encoding="utf-8-sig")
        if kind == "json-list":
            rows = json.loads(text)
        else:
            rows = [
                block.splitlines()[2]
                for block in text.strip().split("\n\n")
                if len(block.splitlines()) >= 3
            ]
        data["transcripts"][key] = {"file": rel, "lines": rows}
    SRC.mkdir(exist_ok=True)
    (SRC / "snippets.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("extracted", len(data["snippets"]), "snippets")


# --------------------------------------------------------------------------- #
# 语法高亮（构建时完成，页面不需要额外的 JS 库）
# --------------------------------------------------------------------------- #
PY_KEYWORDS = {
    "and", "as", "assert", "break", "class", "continue", "def", "elif", "else",
    "except", "finally", "for", "from", "if", "import", "in", "is", "lambda",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "None", "True", "False",
}
PY_TOKEN = re.compile(
    r"""(?P<comment>\#[^\n]*)
      |(?P<string>[rRbBfF]{0,2}(?:'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\"|'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"))
      |(?P<attr>\bm\.[A-Za-z_][A-Za-z0-9_]*)
      |(?P<number>\b\d+(?:\.\d+)?\b)
      |(?P<name>[A-Za-z_][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)


def highlight_python(src: str) -> str:
    out = []
    pos = 0
    prev_word = ""
    for match in PY_TOKEN.finditer(src):
        out.append(html.escape(src[pos : match.start()]))
        kind = match.lastgroup
        text = match.group()
        esc = html.escape(text)
        if kind == "name":
            if text in PY_KEYWORDS:
                out.append(f'<span class="k">{esc}</span>')
            elif prev_word in ("def", "class"):
                out.append(f'<span class="d">{esc}</span>')
            elif text == "self":
                out.append(f'<span class="s-self">{esc}</span>')
            else:
                out.append(esc)
            prev_word = text
        else:
            cls = {"comment": "c", "string": "s", "attr": "a", "number": "n"}[kind]
            out.append(f'<span class="{cls}">{esc}</span>')
            prev_word = ""
        pos = match.end()
    out.append(html.escape(src[pos:]))
    return "".join(out)


SH_TOKEN = re.compile(r"(?P<comment>\#[^\n]*)|(?P<string>\"[^\"\n]*\")|(?P<var>\$\{?[A-Za-z_][A-Za-z0-9_]*\}?)")


def highlight_shell(src: str) -> str:
    out = []
    pos = 0
    for match in SH_TOKEN.finditer(src):
        out.append(html.escape(src[pos : match.start()]))
        cls = {"comment": "c", "string": "s", "var": "a"}[match.lastgroup]
        out.append(f'<span class="{cls}">{html.escape(match.group())}</span>')
        pos = match.end()
    out.append(html.escape(src[pos:]))
    return "".join(out)


def highlight_srt(src: str) -> str:
    out = []
    for line in src.split("\n"):
        if "-->" in line:
            out.append(f'<span class="n">{html.escape(line)}</span>')
        elif line.strip().isdigit():
            out.append(f'<span class="c">{html.escape(line)}</span>')
        else:
            out.append(html.escape(line))
    return "\n".join(out)


def render_code(snippet: dict, label: str) -> str:
    """把一个或多个行号区间渲染成带行号的代码面板。"""
    rel = snippet["file"]
    name = Path(rel).name
    if rel.endswith(".py"):
        lang, painter = "python", highlight_python
    elif rel.endswith(".sh"):
        lang, painter = "shell", highlight_shell
    else:
        lang, painter = "srt", highlight_srt

    all_lines = [ln for block in snippet["blocks"] for ln in block["lines"]]
    indent = min(
        (len(ln) - len(ln.lstrip(" ")) for ln in all_lines if ln.strip()), default=0
    )
    gutter: list[str] = []
    body: list[str] = []
    for i, block in enumerate(snippet["blocks"]):
        if i:
            gutter.append("⋮")
            body.append("")
        text = "\n".join(ln[indent:] for ln in block["lines"])
        body.append(painter(text))
        gutter.extend(str(block["start"] + j) for j in range(len(block["lines"])))
    ranges = "，".join(
        f"第 {b['start']}–{b['start'] + len(b['lines']) - 1} 行" for b in snippet["blocks"]
    )
    return f"""<figure class="code" data-lang="{lang}">
  <figcaption><span class="code-file">{html.escape(rel)}</span><span class="code-range">{ranges}</span></figcaption>
  <div class="code-scroll" tabindex="0" role="region" aria-label="{html.escape(label)}：{html.escape(name)} {ranges}">
    <pre class="code-gutter" aria-hidden="true">{chr(10).join(gutter)}</pre>
    <pre class="code-body"><code>{chr(10).join(body)}</code></pre>
  </div>
</figure>"""


# --------------------------------------------------------------------------- #
# 作品数据（文字取自主站 data/works.json）
# --------------------------------------------------------------------------- #
SUBJECT = {"math": "数学", "physics": "物理", "cs": "计算机"}

# 按成片文件时间排序
ORDER = [
    "definite-integral", "tcp-handshake", "matrix-transform", "pythagoras",
    "projectile", "roadster", "dong-force", "four-stroke",
]

NOTES = {
    "definite-integral": "左边是场景里让矩形越切越密的一段：同一个 make_rects，n 从 4 换成 16 再换成 64。",
    "tcp-handshake": "第一次握手：SYN 包从客户端滑到服务器，两端的状态同时从 CLOSED / LISTEN 变成 SYN_SENT / SYN_RCVD。",
    "matrix-transform": "三个变换共用一个 step()：网格的几何动画和右上角累积矩阵 M 在同一次 self.play 里同步播放。",
    "pythagoras": "四个三角形先绕中心各转 90°，再按三个固定位移平移，中间的空白从 c² 变成 a² 和 b²。",
    "projectile": "把每个残影投到地面，用一排双箭头量出水平间距，间距相等，于是写出 x = v₀t。",
    "roadster": "每句字幕的停留时间由 slot() 给出：配音时长加 0.55 秒。开场这一句里，车沿半圆坡道转到倒挂。",
    "dong-force": "这一集的素材目录里只有成片和字幕文件，没有 scene.py，所以这里放的是旁白字幕原文。",
    "four-stroke": "四冲程的机器画面来自 Anatomy，这一集在 ManimGX 里做的是配音和配乐。左边是配音部分：每个镜头的旁白用 qwen3-tts-flash 合成一条，放在镜头开始后 0.4 秒。",
}

FEATURED = ["pythagoras", "projectile", "roadster"]


def load_works() -> dict:
    data = json.loads((SRC / "works.json").read_text(encoding="utf-8"))
    return {w["id"]: w for w in data}


def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} 秒"
    m, s = divmod(seconds, 60)
    return f"{m} 分 {s} 秒" if s else f"{m} 分钟"


# --------------------------------------------------------------------------- #
# 页面骨架
# --------------------------------------------------------------------------- #
NAV = [
    ("index.html", "首页"),
    ("works.html", "作品"),
    ("how.html", "怎么做的"),
    ("log.html", "更新记录"),
]

MARK = """<svg class="mark" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
  <path d="M5 27H29M5 27V3" fill="none" stroke="currentColor" stroke-width="2.2"/>
  <path d="M5 27Q17 27 27 5" fill="none" stroke="var(--gold)" stroke-width="2.6"/>
</svg>"""


def page(filename: str, title: str, description: str, body: str, extra_head: str = "") -> None:
    full_title = "ManimGX" if filename == "index.html" else f"{title} - ManimGX"
    links = []
    for href, label in NAV:
        current = ' aria-current="page"' if href == filename else ""
        links.append(f'<li><a href="{href}"{current}>{label}</a></li>')
    canonical = SITE_URL + ("" if filename == "index.html" else filename)
    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(full_title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="author" content="TaopleOne">
<meta name="theme-color" content="#EEF2F4">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(full_title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{COVER.format(id='definite-integral')}">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/style.css">
{extra_head}</head>
<body>
<a class="skip" href="#main">跳到正文</a>
<header class="site-head">
  <a class="brand" href="index.html">{MARK}<span>ManimGX</span></a>
  <nav aria-label="站内导航">
    <ul>{''.join(links)}<li><a class="home-link" href="{MAIN_SITE}">回主站</a></li></ul>
  </nav>
</header>
<main id="main">
{body}
</main>
<footer class="site-foot">
  <p>ManimGX 的动画、代码与旁白均由 TaopleOne 制作。更多作品在主站 <a href="{MAIN_SITE}">goaltang.github.io</a>。</p>
  <p class="foot-small">页面里的视频直接从主站加载，点播放才开始下载。</p>
</footer>
<script src="assets/site.js" defer></script>
</body>
</html>
"""
    (ROOT / filename).write_text(doc, encoding="utf-8")
    print("wrote", filename)


def meta_row(w: dict) -> str:
    return f"""<dl class="meta">
  <div><dt>学科</dt><dd>{SUBJECT[w['subject']]}</dd></div>
  <div><dt>适用</dt><dd>{w['level']}</dd></div>
  <div><dt>时长</dt><dd>{fmt_duration(w['duration'])}</dd></div>
</dl>"""


def video(w: dict, label: str | None = None) -> str:
    return f"""<video controls preload="none" playsinline width="1920" height="1080"
    poster="{COVER.format(id=w['id'])}"
    aria-label="{html.escape(label or w['title'])}，动画视频，{fmt_duration(w['duration'])}">
    <source src="{FILM.format(id=w['id'])}" type="video/mp4">
    你的浏览器无法播放这段视频，可以<a href="{FILM.format(id=w['id'])}">直接下载 MP4</a>。
  </video>"""


# --------------------------------------------------------------------------- #
# 首页
# --------------------------------------------------------------------------- #
def build_index(works: dict, data: dict) -> None:
    counts: dict[str, int] = {}
    for w in works.values():
        counts[SUBJECT[w["subject"]]] = counts.get(SUBJECT[w["subject"]], 0) + 1
    subject_line = "、".join(f"{k} {v} 集" for k, v in counts.items())

    featured = []
    for i, wid in enumerate(FEATURED):
        w = works[wid]
        featured.append(f"""<article class="plate plate-{i}">
  <a class="plate-img" href="works.html#{wid}">
    <img src="{COVER.format(id=wid)}" width="960" height="540" loading="lazy" decoding="async"
      alt="《{html.escape(w['title'])}》动画中的一帧">
  </a>
  <div class="plate-text">
    <h3><a href="works.html#{wid}">{html.escape(w['title'])}</a></h3>
    {meta_row(w)}
    <p>{html.escape(w['blurb'])}</p>
  </div>
</article>""")

    hero_code = [
        ("rects = make_rects(4)", 76),
        ('for n, label_text in ((16, "分成 16 个矩形"), (64, "分成 64 个矩形")):', 81),
        ("area = axes.get_area(", 129),
    ]
    code_lines = "\n".join(
        f'<li data-step="{i}"><span class="ln">{ln}</span><code>{highlight_python(t)}</code></li>'
        for i, (t, ln) in enumerate(hero_code)
    )

    body = f"""<section class="hero" aria-labelledby="hero-title">
  <div class="hero-text">
    <h1 id="hero-title">ManimGX</h1>
    <p class="lede">TaopleOne 用 Manim 一帧一帧写出来的知识讲解动画。</p>
    <p>每一集只讲一件事：矩阵怎么变换平面，三角形怎么拼出勾股定理，倒挂的车为什么不掉。画面里的每条线、每个公式都写在 Python 场景代码里。</p>
    <p class="hero-links"><a class="btn" href="works.html">看全部作品</a><a class="quiet" href="how.html">看看是怎么做的</a></p>
  </div>
  <figure class="plot" aria-labelledby="plot-cap">
    <svg id="riemann" viewBox="0 0 640 430" role="img" aria-labelledby="plot-title plot-desc">
      <title id="plot-title">y = x² 在区间 0 到 2 上的面积</title>
      <desc id="plot-desc">坐标系里画出抛物线 y = x²，先用 4 个矩形估计曲线下的面积，再换成 16 个、64 个，最后把面积填满。</desc>
    </svg>
    <figcaption id="plot-cap">
      <ol class="plot-code" aria-label="对应的场景代码，DefiniteIntegralArea_scene.py">
{code_lines}
      </ol>
      <p class="plot-note">照着《定积分：曲线下的面积》的场景代码，在浏览器里重画一遍：矩形从 4 个分到 64 个，最后填满面积。<button type="button" class="replay" id="replay" hidden>重播</button></p>
    </figcaption>
  </figure>
</section>

<section class="about" aria-labelledby="about-title">
  <h2 id="about-title">ManimGX 是什么</h2>
  <div class="about-cols">
    <div class="prose">
      <p>ManimGX 不是一个软件库，而是一组讲解动画。题目来自课本和考试：初中的勾股定理、四冲程汽油机，高中的平抛运动，大学的定积分、矩阵变换，考研 408 的 TCP 三次握手。</p>
      <p>动画都用 Manim 写成。一集就是一个 Scene 类，坐标轴、图形、公式和字幕都是代码里的对象，动画是一次次 <code>self.play(...)</code>。所以改一个数字、挪一个位置，重新渲染就行，不用回到剪辑软件里一帧帧拖。</p>
      <p>后来几集加上了中文配音：旁白先写成一句一句的字幕，配音合成好以后，按每句的时长去排画面。</p>
    </div>
    <dl class="facts">
      <div><dt>已上线</dt><dd>{len(works)} 集</dd></div>
      <div><dt>学科</dt><dd>{subject_line}</dd></div>
      <div><dt>画面</dt><dd>1920 × 1080，大多是 60 帧</dd></div>
      <div><dt>最长一集</dt><dd>平抛运动，{fmt_duration(works['projectile']['duration'])}</dd></div>
    </dl>
  </div>
</section>

<section class="featured" aria-labelledby="featured-title">
  <h2 id="featured-title">先看这三集</h2>
  <div class="plates">
{''.join(featured)}
  </div>
  <p class="more"><a href="works.html">全部 {len(works)} 集，每一集都配了对应的场景代码</a></p>
</section>"""
    page(
        "index.html",
        "首页",
        "ManimGX：TaopleOne 用 Manim 制作的数学、物理、计算机知识讲解动画，附真实的场景代码。",
        body,
    )


# --------------------------------------------------------------------------- #
# 作品页
# --------------------------------------------------------------------------- #
def build_works(works: dict, data: dict) -> None:
    sections = []
    for wid in ORDER:
        w = works[wid]
        snip = data["snippets"][wid]
        code_label = "旁白字幕" if snip["file"].endswith(".srt") else "场景代码"
        transcript = ""
        if wid in data["transcripts"]:
            t = data["transcripts"][wid]
            items = "".join(f"<li>{html.escape(x)}</li>" for x in t["lines"])
            transcript = f"""<details class="transcript">
      <summary>旁白全文（{len(t['lines'])} 句）</summary>
      <ol>{items}</ol>
    </details>"""
        sections.append(f"""<section class="work" id="{wid}" data-subject="{w['subject']}" aria-labelledby="t-{wid}">
  <header class="work-head">
    <h2 id="t-{wid}">{html.escape(w['title'])}</h2>
    {meta_row(w)}
    <p class="blurb">{html.escape(w['blurb'])}</p>
  </header>
  <div class="pair">
    {render_code(snip, f"《{w['title']}》的{code_label}")}
    <figure class="film">
      {video(w)}
      <figcaption>{html.escape(NOTES[wid])}</figcaption>
    </figure>
  </div>
  {transcript}
</section>""")

    filters = [("all", "全部")] + [(k, v) for k, v in SUBJECT.items()]
    buttons = "".join(
        f'<button type="button" data-filter="{k}" aria-pressed="{"true" if k == "all" else "false"}">{v}</button>'
        for k, v in filters
    )
    body = f"""<section class="page-intro">
  <h1>作品</h1>
  <p>按完成时间排列。每一集左边是从场景代码里截出来的一段，右边是这段代码画出来的动画。行号就是源文件里的行号。</p>
  <div class="filter" role="group" aria-label="按学科筛选">{buttons}</div>
  <p class="filter-status" id="filter-status" aria-live="polite">共 {len(ORDER)} 集</p>
</section>
{''.join(sections)}"""
    page(
        "works.html",
        "作品",
        "ManimGX 全部作品：每一集的 Manim 场景代码片段与对应的动画视频并排对照。",
        body,
    )


# --------------------------------------------------------------------------- #
# 怎么做的
# --------------------------------------------------------------------------- #
def build_how(works: dict, data: dict) -> None:
    s = data["snippets"]
    body = f"""<section class="page-intro">
  <h1>怎么做的</h1>
  <p>下面每一步都配了一段真实代码，出自 ManimGX 素材目录里的场景文件和脚本。从写场景到拿到带配音的成片，大致是这样一条路。</p>
</section>

<ol class="steps">
<li class="step">
  <h2>写一个场景</h2>
  <div class="step-body">
    <div class="prose">
      <p>每一集是一个 <code>Scene</code> 子类，画面全部写在 <code>construct()</code> 里。<code>self.play(...)</code> 播一段动画，<code>run_time</code> 定它播多久，<code>self.wait()</code> 停一下让人看清。场景文件开头写着 <code>import manimgx as m</code>，文件头注释说明它兼容 Manim CE 0.22 的公共 API，所以 <code>Text</code>、<code>MathTex</code>、<code>Axes</code> 这些都是 Manim 里的老面孔。</p>
      <p>渲染一集只要一条命令，场景文件的注释里都写着，例如 <code>manimgx render scene.py PythagoreanProof</code>。</p>
    </div>
    <div class="codes">
    {render_code(s['how-scene'], '定积分场景的开头')}
    </div>
  </div>
</li>

<li class="step">
  <h2>定好版面的规矩</h2>
  <div class="step-body">
    <div class="prose">
      <p>成片固定 1920 × 1080。画面上下各留一条字幕带，图形不许伸进去，用 <code>TOP_LIMIT</code> 和 <code>BOTTOM_LIMIT</code> 两个常量卡住。</p>
      <p>中文最怕渲染成方块。场景会先用 <code>fc-list</code> 问系统装了哪些中文字体，再从候选名单里挑第一个真实存在的。标签底下还会垫一块深色底，免得被线条压住。</p>
    </div>
    <div class="codes">
    {render_code(s['how-config'], '勾股定理场景的版面设置')}
    {render_code(s['how-font'], 'Roadster 场景的字体挑选与标签底色')}
    </div>
  </div>
</li>

<li class="step">
  <h2>先把内容算对，再画</h2>
  <div class="step-body">
    <div class="prose">
      <p>有些题目的每一步都能算出来，就先用纯 Python 算一遍，再让动画照着结果走。LRU 页面置换那一集，先模拟 12 次访问，用 <code>assert</code> 核对每一步内存里的页、缺页 9 次、命中 3 次，以及 FIFO 缺页 10 次。核对不过，场景根本不会开始渲染。</p>
      <p>LRU 这一集的场景代码和字幕已经写好，素材目录里还没有导出的成片，所以暂时没有上线。</p>
    </div>
    <div class="codes">
    {render_code(s['how-lru'], 'LRU 场景里的模拟与核对')}
    </div>
  </div>
</li>

<li class="step">
  <h2>写旁白，按配音排时间</h2>
  <div class="step-body">
    <div class="prose">
      <p>带配音的几集，旁白就是字幕。以《倒挂的车为什么不掉》为例：24 句旁白写在 <code>CAPTIONS</code> 列表里，顺序就是时间轴。配音合成以后，每句的时长存进 <code>durations.json</code>，场景读进来，每句字幕在屏幕上停留“配音时长 + 0.55 秒”。还没有配音时，就按每个字 0.25 秒先估一个。</p>
      <p>渲染结束时，场景再把每句的实际起止时间写进 <code>timings.json</code>，用来对齐配音和字幕文件。</p>
    </div>
    <div class="codes">
    {render_code(s['how-captions'], 'Roadster 场景的旁白列表与停留时间')}
    {render_code(s['how-timings'], 'Roadster 场景写出每句起止时间')}
    </div>
  </div>
</li>

<li class="step">
  <h2>配音和配乐</h2>
  <div class="step-body">
    <div class="prose">
      <p>素材目录里留着 qwen3 两个音色 Cherry 和 Serena 的试听样本。四冲程汽油机那一集的脚本写得最完整：每个镜头的旁白用 <code>qwen3-tts-flash</code> 的 Serena 音色合成一条，放进对应镜头的起点后 0.4 秒；背景音乐不用现成曲子，而是用 numpy 按四个和弦循环合成。</p>
      <p>最后用 ffmpeg 混音：<code>adelay</code> 把每句旁白挪到它的时间点，<code>sidechaincompress</code> 让有人说话时音乐自动压低，<code>loudnorm</code> 把整体响度统一到 -16 LUFS。同时还导出一版只有背景音乐的。</p>
      <p>LatentLoop 那一集原本打算用 Gemini 的语音合成，免费额度当天用完，所以两个版本目前都没有配音，也还没上线。</p>
    </div>
    <div class="codes">
    {render_code(s['how-mix'], '四冲程的背景音乐与混音')}
    </div>
  </div>
</li>

<li class="step">
  <h2>导出</h2>
  <div class="step-body">
    <div class="prose">
      <p>成片是 1920 × 1080 的 MP4，大多是 60 帧，最早的定积分是 30 帧。Roadster 还另外导出了 1280 × 720 的手机版，并附 SRT 字幕文件。</p>
      <p>每集的封面不是另外画的，而是用 ffmpeg 在成片 75% 的位置截一帧。这个网站上播放的视频和封面，都直接引用主站 goaltang.github.io 上的版本。</p>
    </div>
    <div class="codes">
    {render_code(s['how-poster'], '截封面的脚本')}
    </div>
  </div>
</li>
</ol>"""
    page(
        "how.html",
        "怎么做的",
        "ManimGX 的制作流程：Manim 场景代码、旁白与配音、混音和导出，每一步都附真实代码。",
        body,
    )


# --------------------------------------------------------------------------- #
# 更新记录
# --------------------------------------------------------------------------- #
LOG = [
    ("2026-10-31", [
        ("这个网站上线，收录已发布的 8 集。", None),
    ]),
    ("2026-10-30", [
        ("用 ffmpeg 在 8 部成片 75% 的位置各截一帧，做成封面。", None),
    ]),
    ("2026-10-28", [
        ("四冲程汽油机：给 Anatomy 做的机器动画配上旁白和背景音乐，出了配音版和纯音乐版，各 58 秒。", "four-stroke"),
    ]),
    ("2026-10-27", [
        ("侗族榫卯：力怎么传下去，51 秒，附 13 句字幕。", "dong-force"),
    ]),
    ("2026-10-17", [
        ("倒挂的车为什么不掉：只讲原理的新版 RoadsterPrinciple，带配音，另有 1280 × 720 手机版。", "roadster"),
    ]),
    ("2026-10-16", [
        ("Roadster 第一版 RoadsterColdGas 出片，晚上加了配音版和手机版。", None),
        ("试听 qwen3 的 Cherry、Serena 两个配音音色。", None),
        ("LatentLoop 3D 讲解做了两个版本，各约 3 分钟，暂无配音，未上线。", None),
    ]),
    ("2026-10-15", [
        ("定积分：曲线下的面积，系列里最早的一部成片。", "definite-integral"),
        ("TCP 三次握手。", "tcp-handshake"),
        ("矩阵如何变换平面。", "matrix-transform"),
        ("勾股定理：拼图证明，2 分 30 秒。", "pythagoras"),
        ("LRU 页面置换：场景代码和字幕完成，成片未导出。", None),
        ("平抛运动，2 分 36 秒，是目前最长的一集。", "projectile"),
    ]),
]


def build_log(works: dict, data: dict) -> None:
    days = []
    for date, items in LOG:
        rows = []
        for text, wid in items:
            if wid:
                rows.append(f'<li><a href="works.html#{wid}">{html.escape(works[wid]["title"])}</a><span>{html.escape(text)}</span></li>')
            else:
                rows.append(f'<li class="plain"><span>{html.escape(text)}</span></li>')
        y, mth, d = date.split("-")
        days.append(f"""<li class="day">
  <h2><time datetime="{date}">{int(mth)} 月 {int(d)} 日</time></h2>
  <ul>{''.join(rows)}</ul>
</li>""")
    body = f"""<section class="page-intro">
  <h1>更新记录</h1>
  <p>按素材目录里的文件时间整理，新的在上。标了链接的是已经上线、能在作品页看到的。</p>
</section>
<ol class="log" reversed>
{''.join(days)}
</ol>"""
    page(
        "log.html",
        "更新记录",
        "ManimGX 更新记录：按素材目录的文件时间整理的每一集完成日期。",
        body,
    )


def build_404() -> None:
    body = """<section class="page-intro">
  <h1>这个地址没有页面</h1>
  <p>可能是链接写错了。可以回到<a href="./">首页</a>，或者直接去<a href="works.html">作品</a>页。</p>
</section>"""
    page("404.html", "找不到页面", "ManimGX：这个地址没有页面。", body,
         extra_head='<base href="/manimgx/">\n')


def main() -> None:
    if "--extract" in sys.argv:
        extract()
    data = json.loads((SRC / "snippets.json").read_text(encoding="utf-8"))
    works = load_works()
    build_index(works, data)
    build_works(works, data)
    build_how(works, data)
    build_log(works, data)
    build_404()


if __name__ == "__main__":
    main()
