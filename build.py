#!/usr/bin/env python3
"""Build the BlueCore blog from posts/*.md. Standard library only (runs on macOS /usr/bin/python3).

    ./build.py            publish build: writes blog/ and the homepage blog blocks; drafts are skipped
    ./build.py --preview  full site copy in _preview/ (gitignored) with drafts included, for review

Post file: posts/YYYY-MM-DD-some-slug.md, starting with front matter:

    ---
    title: Post title
    date: 2026-09-15
    summary: One sentence for lists, the feed and the meta description.
    draft: true            # optional; true keeps the post off the public site
    ---

blog/ is generated in full on every run. Never edit it by hand.
"""
import datetime
import html
import re
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / 'posts'
SITE_URL = 'https://bluecore.joburg'
LATEST_COUNT = 3
PREVIEW_DIR = ROOT / '_preview'
# Files and folders copied into _preview/ so the preview is a complete site.
PREVIEW_COPY = ['index.html', 'site.css', 'chat.js', 'intel.js', 'favicon.svg', 'robots.txt', 'assets']

FILENAME_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$')


class BuildError(Exception):
    pass


# ---------------------------------------------------------------- Markdown subset
# Supported: ## headings (# is demoted to h2; the post title is the page h1), paragraphs,
# - / * bullet lists, 1. numbered lists (one level, no nesting), > quotes, ``` fenced code,
# pipe tables, --- rules, `code`, **bold**, *em* / _em_, [links](url), ![images](url).
# Raw HTML is escaped, never passed through.

def esc(s):
    return html.escape(s, quote=True)


SAFE_URL_RE = re.compile(r'^(https?://|mailto:|/|#|\.\.?/)', re.I)


def safe_url(url):
    return url if SAFE_URL_RE.match(html.unescape(url)) else '#'


def inline(text):
    stash = []

    def keep(fragment):
        stash.append(fragment)
        return '\x00%d\x00' % (len(stash) - 1)

    text = re.sub(r'`([^`]+)`', lambda m: keep('<code>' + esc(m.group(1)) + '</code>'), text)
    text = esc(text)
    text = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)',
                  lambda m: keep('<img src="%s" alt="%s" loading="lazy">' % (safe_url(m.group(2)), m.group(1))), text)
    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)',
                  lambda m: '<a href="%s">%s</a>' % (safe_url(m.group(2)), m.group(1)), text)
    text = re.sub(r'\*\*(?=\S)(.+?)(?<=\S)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])', r'<em>\1</em>', text)
    text = re.sub(r'(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])', r'<em>\1</em>', text)
    # Restore repeatedly: a stashed image can sit inside link text.
    while '\x00' in text:
        text = re.sub(r'\x00(\d+)\x00', lambda m: stash[int(m.group(1))], text)
    return text


def slugify(text):
    s = re.sub(r'<[^>]+>', '', text).lower()
    s = re.sub(r'&[a-z]+;|&#\d+;', '', s)
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'section'


HEADING_RE = re.compile(r'^(#{1,4})\s+(.+?)\s*#*\s*$')
UL_RE = re.compile(r'^[-*]\s+(.*)$')
OL_RE = re.compile(r'^\d+\.\s+(.*)$')
HR_RE = re.compile(r'^(?:-{3,}|\*{3,})\s*$')
TABLE_SEP_RE = re.compile(r'^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$')


def split_row(line):
    """Split a pipe-table row; a | inside `code` or written as \\| stays in the cell."""
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|') and not line.endswith('\\|'):
        line = line[:-1]
    cells, cur, in_code, i = [], [], False, 0
    while i < len(line):
        ch = line[i]
        if ch == '\\' and line[i + 1:i + 2] == '|':
            cur.append('|')
            i += 2
            continue
        if ch == '`':
            in_code = not in_code
        if ch == '|' and not in_code:
            cells.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append(''.join(cur).strip())
    return cells


def is_block_start(lines, i):
    line = lines[i]
    return bool(line.startswith('```') or HEADING_RE.match(line) or UL_RE.match(line) or OL_RE.match(line)
                or line.startswith('>') or HR_RE.match(line)
                or (line.startswith('|') and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1])))


def markdown(text, used_ids=None):
    used_ids = set() if used_ids is None else used_ids
    lines = text.replace('\r\n', '\n').split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        if line.startswith('```'):
            lang = line[3:].strip()
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                body.append(lines[i])
                i += 1
            if i == len(lines):
                raise BuildError('unclosed ``` code fence')
            i += 1
            cls = ' class="language-%s"' % esc(lang) if lang else ''
            out.append('<pre><code%s>%s</code></pre>' % (cls, esc('\n'.join(body))))
            continue

        m = HEADING_RE.match(line)
        if m:
            level = max(2, len(m.group(1)))
            content = inline(m.group(2))
            anchor = base = slugify(content)
            n = 2
            while anchor in used_ids:
                anchor = '%s-%d' % (base, n)
                n += 1
            used_ids.add(anchor)
            out.append('<h%d id="%s">%s</h%d>' % (level, anchor, content, level))
            i += 1
            continue

        if HR_RE.match(line):
            out.append('<hr>')
            i += 1
            continue

        if line.startswith('|') and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1]):
            head = split_row(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(split_row(lines[i]))
                i += 1
            parts = ['<div class="table-wrap"><table><thead><tr>']
            parts += ['<th>%s</th>' % inline(c) for c in head]
            parts.append('</tr></thead><tbody>')
            for row in rows:
                row = (row + [''] * len(head))[:len(head)]
                parts.append('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in row) + '</tr>')
            parts.append('</tbody></table></div>')
            out.append(''.join(parts))
            continue

        if line.startswith('>'):
            quoted = []
            while i < len(lines) and lines[i].startswith('>'):
                quoted.append(re.sub(r'^>\s?', '', lines[i]))
                i += 1
            out.append('<blockquote>%s</blockquote>' % markdown('\n'.join(quoted), used_ids))
            continue

        for tag, item_re in (('ul', UL_RE), ('ol', OL_RE)):
            if item_re.match(line):
                items = []
                while i < len(lines):
                    m = item_re.match(lines[i])
                    if m:
                        items.append(m.group(1))
                    elif lines[i].startswith('  ') and lines[i].strip() and items:
                        items[-1] += ' ' + lines[i].strip()
                    else:
                        break
                    i += 1
                out.append('<%s>%s</%s>' % (tag, ''.join('<li>%s</li>' % inline(t) for t in items), tag))
                break
        else:
            para = [line.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not is_block_start(lines, i):
                para.append(lines[i].strip())
                i += 1
            out.append('<p>%s</p>' % inline(' '.join(para)))
    return '\n'.join(out)


# ---------------------------------------------------------------- Posts

def parse_post(path):
    m = FILENAME_RE.match(path.name)
    if not m:
        raise BuildError('%s: name must be YYYY-MM-DD-lowercase-slug.md' % path.name)
    raw = path.read_text(encoding='utf-8')
    fm = re.match(r'^---\n(.*?)\n---\n', raw.replace('\r\n', '\n'), re.S)
    if not fm:
        raise BuildError('%s: missing --- front matter ---' % path.name)
    meta = {}
    for line in fm.group(1).split('\n'):
        line = re.sub(r'\s+#.*$', '', line).rstrip()
        if not line.strip():
            continue
        key, sep, value = line.partition(':')
        if not sep:
            raise BuildError('%s: bad front matter line: %r' % (path.name, line))
        meta[key.strip().lower()] = value.strip().strip('"\'')
    for key in ('title', 'date', 'summary'):
        if not meta.get(key):
            raise BuildError('%s: front matter needs %s' % (path.name, key))
    try:
        date = datetime.date.fromisoformat(meta['date'])
    except ValueError:
        raise BuildError('%s: date must be YYYY-MM-DD' % path.name)
    draft = meta.get('draft', 'false').lower()
    if draft not in ('true', 'false'):
        raise BuildError('%s: draft must be true or false' % path.name)
    body = raw.replace('\r\n', '\n')[fm.end():]
    try:
        body_html = markdown(body)
    except BuildError as e:
        raise BuildError('%s: %s' % (path.name, e))
    words = len(re.findall(r'\w+', body))
    return {
        'slug': m.group(2),
        'title': meta['title'],
        'summary': meta['summary'],
        'date': date,
        'draft': draft == 'true',
        'html': body_html,
        'minutes': max(1, round(words / 200)),
        'source': path.name,
    }


def load_posts(include_drafts):
    posts = [parse_post(p) for p in sorted(POSTS.glob('*.md'))] if POSTS.is_dir() else []
    seen = {}
    for p in posts:
        if p['slug'] in seen:
            raise BuildError('duplicate slug %r in %s and %s' % (p['slug'], seen[p['slug']], p['source']))
        seen[p['slug']] = p['source']
    kept = [p for p in posts if include_drafts or not p['draft']]
    kept.sort(key=lambda p: (p['date'], p['slug']), reverse=True)
    return kept, len(posts) - len(kept)


# ---------------------------------------------------------------- Templates

def human_date(d):
    return '%d %s %d' % (d.day, d.strftime('%b'), d.year)


def post_url(p):
    return '/blog/%s/' % p['slug']


def draft_badge(p):
    return '<span class="draft-badge">DRAFT</span>' if p['draft'] else ''


def post_list(posts, heading_tag='h3'):
    items = []
    for p in posts:
        items.append(
            '<li class="post-item">'
            '<p class="post-meta"><time datetime="%s">%s</time> · %d min read%s</p>'
            '<%s><a href="%s">%s</a></%s>'
            '<p>%s</p>'
            '</li>' % (p['date'].isoformat(), human_date(p['date']), p['minutes'], draft_badge(p),
                       heading_tag, post_url(p), esc(p['title']), heading_tag, esc(p['summary'])))
    return '<ul class="post-list">%s</ul>' % ''.join(items)


def page(title, description, path, body, og_type='website', extra_head='', noindex=False):
    robots = '<meta name="robots" content="noindex">\n' if noindex else ''
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<meta name="theme-color" content="#020610">
%(robots)s<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="canonical" href="%(url)s">
<link rel="alternate" type="application/rss+xml" title="BlueCore blog" href="/blog/feed.xml">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(url)s">
<meta property="og:type" content="%(og_type)s">
%(extra)s<link rel="stylesheet" href="/site.css">
</head>
<body class="blog">
  <main>
    <nav class="topnav" aria-label="Site">
      <a class="topnav-home" href="/">BLUECORE</a>
      <a href="/blog/"%(blog_current)s>Blog</a>
    </nav>
%(body)s
  </main>

  <footer>
    BlueCore, Johannesburg. 2026.
  </footer>

  <div class="scanlines" aria-hidden="true"></div>
<script src="/chat.js" defer></script>
</body>
</html>
''' % {
        'title': esc(title), 'desc': esc(description), 'url': SITE_URL + path, 'og_type': og_type,
        'robots': robots, 'extra': extra_head, 'body': body,
        'blog_current': ' aria-current="page"' if path == '/blog/' else '',
    }


def render_post(p):
    body = '''    <article>
      <header class="blog-head">
        <h1>%s</h1>
        <p class="post-meta"><time datetime="%s">%s</time> · %d min read%s</p>
      </header>
      <div class="prose">
%s
      </div>
    </article>
    <p class="post-foot"><a href="/blog/">&lt; All posts</a><a href="/blog/feed.xml">RSS feed</a></p>''' % (
        esc(p['title']), p['date'].isoformat(), human_date(p['date']), p['minutes'], draft_badge(p), p['html'])
    extra = '<meta property="article:published_time" content="%s">\n' % p['date'].isoformat()
    return page(p['title'] + ' | BlueCore', p['summary'], post_url(p), body, 'article', extra, noindex=p['draft'])


def render_index(posts):
    listing = post_list(posts, 'h2') if posts else '<p class="post-meta">No posts yet.</p>'
    body = '''    <header class="blog-head">
      <h1>Blog</h1>
      <p class="lede">Notes from the BlueCore lab: network access control, identity and policy, measured rather than assumed.</p>
    </header>
    <div class="blog-list">
      %s
      <p class="more-link"><a href="/blog/feed.xml">RSS feed</a></p>
    </div>''' % listing
    return page('Blog | BlueCore', 'Notes from the BlueCore lab on network access control, identity and policy.',
                '/blog/', body, noindex=any(p['draft'] for p in posts))


def render_feed(posts):
    now = datetime.datetime.now(datetime.timezone.utc)
    items = []
    for p in posts:
        # Posts carry a date only; publish time is fixed at 08:00 SAST.
        stamp = datetime.datetime.combine(p['date'], datetime.time(6, 0), datetime.timezone.utc)
        url = SITE_URL + post_url(p)
        items.append('''    <item>
      <title>%s</title>
      <link>%s</link>
      <guid isPermaLink="true">%s</guid>
      <pubDate>%s</pubDate>
      <description>%s</description>
    </item>''' % (xml_escape(p['title']), url, url, stamp.strftime('%a, %d %b %Y %H:%M:%S +0000'),
                  xml_escape(p['summary'])))
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>BlueCore blog</title>
    <link>%s/blog/</link>
    <atom:link href="%s/blog/feed.xml" rel="self" type="application/rss+xml"/>
    <description>Notes from the BlueCore lab on network access control, identity and policy.</description>
    <language>en-za</language>
    <lastBuildDate>%s</lastBuildDate>
%s
  </channel>
</rss>
''' % (SITE_URL, SITE_URL, now.strftime('%a, %d %b %Y %H:%M:%S +0000'), '\n'.join(items))


def replace_block(text, name, content):
    start, end = '<!-- blog:%s -->' % name, '<!-- /blog:%s -->' % name
    pattern = re.compile(r'([ \t]*)%s.*?%s' % (re.escape(start), re.escape(end)), re.S)
    m = pattern.search(text)
    if not m or len(pattern.findall(text)) != 1:
        raise BuildError('index.html must contain exactly one %s ... %s block' % (start, end))
    indent = m.group(1)
    inner = ('\n' + content) if content else ''
    return text[:m.start()] + indent + start + inner + '\n' + indent + end + text[m.end():]


def update_homepage(index_path, posts):
    text = index_path.read_text(encoding='utf-8')
    if posts:
        nav = '      <a href="/blog/">Blog</a>'
        latest = '''    <section class="section" id="latest">
      <h2>Latest posts</h2>
      %s
      <p class="more-link"><a href="/blog/">All posts &gt;</a></p>
    </section>''' % post_list(posts[:LATEST_COUNT])
    else:
        nav = latest = ''
    text = replace_block(text, 'nav', nav)
    text = replace_block(text, 'latest', latest)
    index_path.write_text(text, encoding='utf-8')


# ---------------------------------------------------------------- Main

def build(out_root, include_drafts):
    posts, skipped = load_posts(include_drafts)
    blog = out_root / 'blog'
    if blog.exists():
        shutil.rmtree(blog)
    blog.mkdir(parents=True)
    for p in posts:
        d = blog / p['slug']
        d.mkdir()
        (d / 'index.html').write_text(render_post(p), encoding='utf-8')
    (blog / 'index.html').write_text(render_index(posts), encoding='utf-8')
    (blog / 'feed.xml').write_text(render_feed([p for p in posts if not p['draft']]), encoding='utf-8')
    update_homepage(out_root / 'index.html', posts)
    return posts, skipped


def main(argv):
    preview = '--preview' in argv
    unknown = [a for a in argv if a != '--preview']
    if unknown:
        print(__doc__)
        return 2
    try:
        if preview:
            if PREVIEW_DIR.exists():
                shutil.rmtree(PREVIEW_DIR)
            PREVIEW_DIR.mkdir()
            for name in PREVIEW_COPY:
                src = ROOT / name
                if src.is_dir():
                    shutil.copytree(src, PREVIEW_DIR / name)
                elif src.exists():
                    shutil.copy2(src, PREVIEW_DIR / name)
            posts, _ = build(PREVIEW_DIR, include_drafts=True)
            print('preview built in _preview/ with %d post(s), drafts included.' % len(posts))
            print('  python3 -m http.server 8090 --directory _preview   then open http://127.0.0.1:8090/')
        else:
            posts, skipped = build(ROOT, include_drafts=False)
            print('built %d post(s); %d draft(s) skipped.' % (len(posts), skipped))
    except BuildError as e:
        print('build failed: %s' % e, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
