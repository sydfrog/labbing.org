#!/usr/bin/env python3
"""
build.py - compiles posts/*.md into static HTML pages + index + about.

Each markdown post needs a front matter block:

---
title: My Post Title
date: 2026-06-11
tag: LAB
category: Networking
excerpt: One line summary shown on the index page.
---

Markdown body follows. Code fences support a language label: ```bash
Run:  python3 build.py
"""

import re
import os
import random
import datetime

random.seed(2026)  # deterministic rain layout across rebuilds

RAIN_COLUMNS = 14
RAIN_CHARS = "0123456789abcdef"


def rain_html():
    cols = []
    for i in range(RAIN_COLUMNS):
        left = round(random.uniform(2, 97), 1)
        dur = round(random.uniform(16, 34), 1)
        delay = round(random.uniform(-dur, 0), 1)
        opacity = round(random.uniform(0.035, 0.085), 3)
        size = random.choice([11, 12, 13])
        chars = "&#10;".join(random.choice(RAIN_CHARS) for _ in range(random.randint(16, 26)))
        hue_cls = "rain-alt" if random.random() < 0.25 else ""
        cols.append(
            f'<span class="{hue_cls}" style="left:{left}%;animation-duration:{dur}s;'
            f'animation-delay:{delay}s;opacity:{opacity};font-size:{size}px">{chars}</span>'
        )
    return '<div class="bg-rain" aria-hidden="true">' + "".join(cols) + "</div>"

ROOT = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(ROOT, "posts")
OUT_DIR = ROOT

SITE_TITLE = "lab.notes"
SITE_HOST = "chris@lab"
SITE_EYEBROW_CMD = "ls ./posts --sort=date"
HERO_HEADLINE = "Build it. Break it. <em>Write it down.</em>"
HERO_LEDE = (
    "Hands-on write-ups on VMware Cloud Foundation, NSX, vSAN, and the "
    "automation that holds a homelab together. Written down so future-me "
    "doesn't have to debug it twice."
)
SITE_AUTHOR = "Chris"
WORDS_PER_MIN = 200
HUES = 5


def hue(name):
    """Deterministically map a tag/category name to one of the colour hues."""
    return sum(name.lower().encode()) % HUES

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}style.css">
<script>(function() {{ var t = localStorage.getItem("theme"); if (t) document.documentElement.dataset.theme = t; }})();</script>
</head>
<body>
{rain}
<header class="site">
  <div class="wrap">
    <a class="site-title" href="{root}index.html"><span class="status-dot" aria-hidden="true"></span>{site_title}<span class="dot">_</span></a>
    <nav class="site-nav">
      <a href="{root}index.html" class="{home_active}">posts</a>
      <a href="{root}about.html" class="{about_active}">about</a>
      <button class="theme-btn" id="theme-toggle" aria-label="Toggle colour scheme"><span class="sw" aria-hidden="true"></span><span id="theme-label">light</span></button>
    </nav>
  </div>
</header>
<main class="wrap">
{content}
</main>
<footer class="site">
  <div class="wrap"><span class="prompt">$</span>echo "&copy; {year} {author} &middot; markdown in, html out, served from the edge"</div>
</footer>
<script>
(function() {{
  var btn = document.getElementById("theme-toggle");
  var label = document.getElementById("theme-label");
  function sync() {{ label.textContent = document.documentElement.dataset.theme === "light" ? "dark" : "light"; }}
  sync();
  btn.addEventListener("click", function() {{
    var next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("theme", next);
    sync();
  }});
}})();
</script>
</body>
</html>
"""


def parse_post(path):
    # utf-8-sig strips the BOM Windows Notepad adds; normalise CRLF line endings
    text = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    fname = os.path.basename(path)
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if m:
        front, body = m.groups()
        meta = {}
        for line in front.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    else:
        # No front matter: warn, then build the post anyway with defaults
        print(f"WARNING: {fname} has no front matter. Using defaults.")
        print("         Add a block like this at the very top of the file:")
        print("         ---")
        print("         title: My Post Title")
        print(f"         date: {datetime.date.today()}")
        print("         tag: LAB")
        print("         category: General")
        print("         excerpt: One line summary for the homepage.")
        print("         ---")
        meta = {}
        body = text
    slug = os.path.splitext(fname)[0]
    meta.setdefault("title", slug.replace("-", " ").replace("_", " ").title())
    meta.setdefault("date", str(datetime.date.today()))
    meta.setdefault("tag", "POST")
    meta.setdefault("category", "General")
    meta.setdefault("excerpt", "")
    try:
        datetime.datetime.strptime(meta["date"], "%Y-%m-%d")
    except ValueError:
        print(f"WARNING: {fname} has date '{meta['date']}', expected YYYY-MM-DD. Using today.")
        meta["date"] = str(datetime.date.today())
    meta["body"] = body.strip()
    meta["slug"] = slug
    word_count = len(re.findall(r"\w+", meta["body"]))
    meta["read_mins"] = max(1, round(word_count / WORDS_PER_MIN))
    return meta


def md_to_html(md):
    """Minimal markdown to HTML converter covering common needs."""
    lines = md.split("\n")
    html = []
    in_code = False
    in_list = None

    def close_list():
        nonlocal in_list
        if in_list:
            html.append(f"</{in_list}>")
            in_list = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                close_list()
                lang = stripped[3:].strip() or "shell"
                html.append(
                    f'<div class="codeblock"><div class="lang-bar">{lang}</div><pre><code>'
                )
                in_code = True
            else:
                html.append("</code></pre></div>")
                in_code = False
            continue
        if in_code:
            html.append(
                line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            continue

        if stripped.startswith("> "):
            close_list()
            content = stripped[2:]
            content = re.sub(r"^\[!\w+\]\s*", "", content)
            html.append(f'<div class="callout"><div>{inline(content)}</div></div>')
            continue

        m = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if m:
            close_list()
            level = min(len(m.group(1)) + 1, 3)
            html.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            continue

        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            if in_list != "ul":
                close_list()
                html.append("<ul>")
                in_list = "ul"
            html.append(f"<li>{inline(m.group(1))}</li>")
            continue
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            if in_list != "ol":
                close_list()
                html.append("<ol>")
                in_list = "ol"
            html.append(f"<li>{inline(m.group(1))}</li>")
            continue

        m = re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped)
        if m:
            close_list()
            html.append(f'<img alt="{m.group(1)}" src="{m.group(2)}" loading="lazy">')
            continue

        if not stripped:
            close_list()
            continue

        close_list()
        html.append(f"<p>{inline(stripped)}</p>")

    close_list()
    return "\n".join(html)


def inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text


def fmt_date(d):
    dt = datetime.datetime.strptime(d, "%Y-%m-%d")
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


def render_page(title, description, content, root="", active=""):
    return PAGE_TEMPLATE.format(
        title=title,
        description=description,
        content=content,
        rain=RAIN,
        site_title=SITE_TITLE,
        root=root,
        home_active="active" if active == "home" else "",
        about_active="active" if active == "about" else "",
        year=datetime.date.today().year,
        author=SITE_AUTHOR,
    )


def meta_line(p, is_new=False):
    t = p.get("tag", "POST")
    badge = '<span class="badge-new">new</span>' if is_new else ""
    return (
        f'<div class="post-meta"><span class="tag hue-{hue(t)}">{t}</span>{badge}'
        f"<span>{fmt_date(p['date'])}</span>"
        f'<span class="mid">&middot;</span>'
        f"<span>{p['read_mins']} min read</span></div>"
    )


RAIN = rain_html()


def main():
    posts = []
    for fname in sorted(os.listdir(POSTS_DIR)):
        if fname.endswith(".md"):
            posts.append(parse_post(os.path.join(POSTS_DIR, fname)))
    posts.sort(key=lambda p: p["date"], reverse=True)

    # Post pages
    for p in posts:
        body_html = md_to_html(p["body"])
        article = f"""<article class="post">
  {meta_line(p)}
  <h1>{p['title']}</h1>
{body_html}
  <a class="back-link" href="../index.html">&larr; cd ..</a>
</article>"""
        out = render_page(
            f"{p['title']} | {SITE_TITLE}", p.get("excerpt", ""), article, root="../"
        )
        with open(
            os.path.join(OUT_DIR, "posts", f"{p['slug']}.html"), "w", encoding="utf-8"
        ) as f:
            f.write(out)
        print(f"wrote posts/{p['slug']}.html")

    # Stats
    total_articles = len(posts)
    cat_counts = {}
    for p in posts:
        c = p.get("category", "General")
        cat_counts[c] = cat_counts.get(c, 0) + 1
    years = sorted(set(p["date"][:4] for p in posts))
    writing_since = years[0] if years else str(datetime.date.today().year)
    total_minutes = sum(p["read_mins"] for p in posts)
    if total_minutes >= 60:
        reading_num, reading_unit = f"{total_minutes // 60}", f"h {total_minutes % 60}m"
    else:
        reading_num, reading_unit = f"{total_minutes}", "min"

    topic_items = "\n".join(
        f'    <li><a class="hue-{hue(c)}" href="#latest">{c}<span class="count">{n}</span></a></li>'
        for c, n in sorted(cat_counts.items(), key=lambda x: -x[1])
    )

    hero = f"""<section class="hero">
  <div class="prompt-line"><span class="user">{SITE_HOST}</span><span class="path">:~$</span> <span class="cmd">{SITE_EYEBROW_CMD}</span><span class="cursor" aria-hidden="true"></span></div>
  <h1>{HERO_HEADLINE}</h1>
  <p class="lede">{HERO_LEDE}</p>
  <div class="hero-actions">
    <a class="button" href="#latest">Browse all posts</a>
    <a class="text-link" href="about.html">About this lab</a>
  </div>
  <div class="stats">
    <div class="hue-0"><div class="stat-num">{total_articles}</div><div class="stat-label">Articles</div></div>
    <div class="hue-1"><div class="stat-num">{len(cat_counts)}</div><div class="stat-label">Categories</div></div>
    <div class="hue-3"><div class="stat-num">{writing_since}</div><div class="stat-label">Writing since</div></div>
    <div class="hue-2"><div class="stat-num">{reading_num}<span class="unit">{reading_unit}</span></div><div class="stat-label">Total reading</div></div>
  </div>
</section>
<section class="topics">
  <h2 class="kicker">Browse by topic</h2>
  <ul class="topic-list">
{topic_items}
  </ul>
</section>"""

    cutoff = datetime.date.today() - datetime.timedelta(days=30)
    items = "\n".join(
        f"""  <li class="hue-{hue(p.get('category', p.get('tag', 'POST')))}">
    {meta_line(p, is_new=datetime.datetime.strptime(p['date'], '%Y-%m-%d').date() >= cutoff)}
    <h2><a href="posts/{p['slug']}.html">{p['title']}</a></h2>
    <p class="post-excerpt">{p.get('excerpt', '')}</p>
  </li>"""
        for p in posts
    )

    index_content = f"""{hero}
<div class="section-head" id="latest">
  <h2 class="kicker">Recent posts</h2>
</div>
<ul class="post-list">
{items}
</ul>"""

    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(
            render_page(
                f"{SITE_TITLE} | field notes from a vSphere homelab",
                "Field notes on VCF, NSX, vSAN and homelab automation.",
                index_content,
                active="home",
            )
        )
    print("wrote index.html")

    # About
    about_content = """<article class="post">
  <h1>About this lab</h1>
  <p>This site is a running log of homelab builds, troubleshooting notes,
  and scripts written while working hands-on with VMware Cloud Foundation,
  NSX, vSAN, and the Operations suite.</p>
  <p>Mostly notes-to-self, shared in case they save someone else a few hours.</p>
  <a class="back-link" href="index.html">&larr; cd ..</a>
</article>"""
    with open(os.path.join(OUT_DIR, "about.html"), "w", encoding="utf-8") as f:
        f.write(
            render_page(
                f"About | {SITE_TITLE}",
                "About this homelab blog.",
                about_content,
                active="about",
            )
        )
    print("wrote about.html")


if __name__ == "__main__":
    main()
