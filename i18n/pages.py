#!/usr/bin/env python3
"""Translate the site's hand-written pages without forking them.

The English HTML in public/ stays the source. `extract` pulls every translatable piece out of it
into i18n/pages/<page>/en.json; translators fill i18n/pages/<page>/<lang>.json with the same ids;
`render` splices the translations back into a copy of the English page under public/localized/.

    python3 i18n/pages.py extract              # refresh en.json for every page (and hreflang/switcher)
    python3 i18n/pages.py missing [lang...]    # ids each translation still lacks
    python3 i18n/pages.py check [lang...]      # tags/links intact, nothing left in English
    python3 i18n/pages.py render               # write public/localized/<folder>/<page>.html

What counts as translatable: runs of text plus inline markup (<a>, <strong>, <br>…) between block
tags; alt / title / aria-label / placeholder attributes; description-type <meta> content; and the
prose fields of JSON-LD. Ids are a hash of the English text, so editing a sentence in English makes
it show up in `missing` for every language, and unchanged sentences keep their translations.

Anything between <!-- i18n:skip --> and <!-- /i18n:skip --> is left alone (the language switcher
lives there). Legal pages have their own pipeline (render.py) and are not handled here.
"""
import hashlib
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import LANGS, SWITCHER_SCRIPT, SITE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.normpath(os.path.join(HERE, '..', 'public'))
STORE = os.path.join(HERE, 'pages')

PAGES = ['index.html', 'press.html', '404.html', 'invite.html', 'guides/index.html'] + sorted(
    'guides/' + f for f in os.listdir(os.path.join(PUBLIC, 'guides')) if f != 'index.html')

TOKEN = re.compile(r'(?is)<!--.*?-->|<(script|style)\b[^>]*>.*?</\1\s*>|<![^>]*>|<[^>]+>|[^<]+')
INLINE = {'a', 'strong', 'em', 'b', 'i', 'br', 'span', 'code', 'small', 'sup', 'sub', 'u', 'mark',
          'abbr', 'time', 's', 'wbr'}
VOID = {'br', 'wbr', 'img', 'input', 'meta', 'link', 'hr', 'source'}
ATTRS = re.compile(r'''\s(alt|title|aria-label|placeholder|content)\s*=\s*"([^"]*)"''')
META_KEYS = {'description', 'og:title', 'og:description', 'twitter:title', 'twitter:description',
             'og:image:alt', 'twitter:image:alt'}
LD_KEYS = {'description', 'headline', 'text', 'alternativeHeadline', 'featureList', 'abstract',
           'caption', 'jobTitle'}
LD_NAMED = {'Question', 'HowTo', 'HowToStep', 'HowToSection', 'WebPage', 'Article', 'BlogPosting',
            'CollectionPage', 'ListItem', 'FAQPage', 'ItemList', 'Offer'}
SKIP_ONLY = {'Disconnect', 'Bytehood', 'Bytehood Ltd', 'Bytehood Ltd.', 'Shuaib Khan'}


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def sid(text):
    return hashlib.sha1(text.encode()).hexdigest()[:8]


def wants(text):
    plain = norm(html.unescape(re.sub(r'<[^>]+>', ' ', text)))
    return bool(re.search(r'[^\W\d_]', plain)) and plain not in SKIP_ONLY and not re.fullmatch(r'\S+@\S+', plain)


def tag_name(tok):
    m = re.match(r'</?\s*([a-zA-Z][\w:-]*)', tok)
    return m.group(1).lower() if m else None


def balance(toks):
    """Drop tags at either end that open or close outside the run."""
    def matched(i):
        t = toks[i][2]
        n = tag_name(t)
        if n in VOID or t.endswith('/>'):
            return n != 'br'      # a stray <br> at an edge is layout, not text
        closing = t.startswith('</')
        depth = 0
        rng = range(i + 1, len(toks)) if not closing else range(i - 1, -1, -1)
        for j in rng:
            u = toks[j][2]
            if not u.startswith('<') or tag_name(u) != n:
                continue
            if u.startswith('</') == closing:
                depth += 1
            elif depth == 0:
                return True
            else:
                depth -= 1
        return False
    changed = True
    while toks and changed:
        changed = False
        for idx in (0, -1):
            if toks and (not toks[idx][2].strip() or (toks[idx][2].startswith('<') and not matched(idx % len(toks)))):
                toks.pop(idx)
                changed = True
    return toks


def ld_strings(node, out, parent_type=None):
    if isinstance(node, dict):
        t = node.get('@type')
        t = t[0] if isinstance(t, list) else t
        for k, v in node.items():
            if isinstance(v, str) and (k in LD_KEYS or (k == 'name' and t in LD_NAMED)):
                out.append(v)
            elif k in LD_KEYS and isinstance(v, list):
                out += [x for x in v if isinstance(x, str)]
            else:
                ld_strings(v, out, t)
    elif isinstance(node, list):
        for v in node:
            ld_strings(v, out, parent_type)


def ld_apply(node, tr, lang):
    if isinstance(node, dict):
        t = node.get('@type')
        t = t[0] if isinstance(t, list) else t
        for k, v in list(node.items()):
            if k == 'inLanguage' and isinstance(v, str):
                node[k] = lang
            elif isinstance(v, str) and (k in LD_KEYS or (k == 'name' and t in LD_NAMED)):
                node[k] = tr(v)
            elif k in LD_KEYS and isinstance(v, list):
                node[k] = [tr(x) if isinstance(x, str) else x for x in v]
            else:
                ld_apply(v, tr, lang)
    elif isinstance(node, list):
        for v in node:
            ld_apply(v, tr, lang)


def pieces(src):
    """Yield (start, end, kind, text) for everything translatable in an English page."""
    toks = [(m.start(), m.end(), m.group(0)) for m in TOKEN.finditer(src)]
    run, skipping = [], False

    def flush():
        r = balance(run[:])
        run.clear()
        if r:
            text = src[r[0][0]:r[-1][1]]
            if wants(text):
                yield (r[0][0], r[-1][1], 'body', norm(text))

    for start, end, tok in toks:
        if tok.startswith('<!--'):
            yield from flush()
            if 'i18n:skip' in tok:
                skipping = not tok.strip('<!- >').startswith('/')
            continue
        if skipping:
            continue
        if not tok.startswith('<'):
            run.append((start, end, tok))
            continue
        name = tag_name(tok)
        low = tok[:60].lower()
        if low.startswith('<script'):
            yield from flush()
            if 'ld+json' in low:
                body_start = start + tok.index('>') + 1
                body_end = start + tok.lower().rindex('</script')
                data = json.loads(src[body_start:body_end])
                found = []
                ld_strings(data, found)
                for s in found:
                    if wants(s):
                        yield (body_start, body_end, 'ld', s)
            continue
        if low.startswith('<style') or low.startswith('<!'):
            yield from flush()
            continue
        # attributes on any tag
        is_meta = name == 'meta'
        if is_meta:
            key = re.search(r'''(?:name|property)\s*=\s*"([^"]+)"''', tok)
        for m in ATTRS.finditer(tok):
            a, v = m.group(1), m.group(2)
            if a == 'content' and not (is_meta and key and key.group(1) in META_KEYS):
                continue
            if v.strip() and wants(v):
                yield (start + m.start(2), start + m.end(2), 'attr', norm(v))
        if name in INLINE:
            run.append((start, end, tok))
        else:
            yield from flush()
    yield from flush()


def store_dir(page):
    return os.path.join(STORE, page[:-5])


def load(page, code):
    p = os.path.join(store_dir(page), f'{code}.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


# ---------------------------------------------------------------- hreflang + switcher (English too)

def url_of(page, folder):
    path = '' if page == 'index.html' else ('guides/' if page == 'guides/index.html' else page[:-5])
    return f'{SITE}/{path}' if not folder else f'{SITE}/localized/{folder}/{path}'


def head_block(page):
    alts = [f'<link rel="alternate" hreflang="{e[1]}" href="{url_of(page, e[2][0] if e[2] else None)}">'
            for e in LANGS]
    alts.append(f'<link rel="alternate" hreflang="x-default" href="{url_of(page, None)}">')
    return '<!-- i18n:skip -->\n' + '\n'.join(alts) + '\n<!-- /i18n:skip -->\n'


def switcher_block(code, label):
    opts = ''.join(f'<option value="{c}"{" selected" if c == code else ""}>{lab}</option>'
                   for c, _, _, lab, _ in LANGS)
    script = SWITCHER_SCRIPT % json.dumps({e[0]: list(e[4]) for e in LANGS})
    return (f'<!-- i18n:skip -->\n    <p class="lang-switch"><label for="langSelect">{label}</label> '
            f'<select id="langSelect">{opts}</select></p>\n{script}\n<!-- /i18n:skip -->\n')


SKIP_RE = re.compile(r'<!-- i18n:skip -->.*?<!-- /i18n:skip -->\n?', re.S)


def decorate(src, page, code, label):
    """Strip any earlier hreflang/switcher, then add fresh ones for this language."""
    src = SKIP_RE.sub('', src)
    if page in ('404.html', 'invite.html'):           # not indexable pages: switcher only
        head = ''
    else:
        head = head_block(page)
    src = src.replace('</head>', head + '</head>', 1)
    if '</footer>' in src:
        i = src.index('</footer>')
        j = src.rfind('</div>', 0, i)                   # inside .footer-inner, after the links
        src = src[:j] + switcher_block(code, label) + src[j:]
    return src


# ---------------------------------------------------------------- commands

def labels():
    out = {}
    for code, *_ in LANGS:
        p = os.path.join(HERE, 'privacy', f'{code}.json')
        out[code] = json.load(open(p, encoding='utf-8'))['ui']['language_label']
    return out


def extract():
    lab = labels()
    total = 0
    for page in PAGES:
        path = os.path.join(PUBLIC, page)
        src = open(path, encoding='utf-8').read()
        new = decorate(src, page, 'en', lab['en'])
        if new != src:
            open(path, 'w', encoding='utf-8').write(new)
        en = {}
        for *_, text in pieces(new):
            en.setdefault(sid(text), text)
        os.makedirs(store_dir(page), exist_ok=True)
        json.dump(en, open(os.path.join(store_dir(page), 'en.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        words = sum(len(re.sub(r'<[^>]+>', ' ', t).split()) for t in en.values())
        total += words
        print(f'{page:50} {len(en):4} strings {words:6} words')
    print(f'{"total":50}      {total:6} words')


def codes(argv):
    return argv or [c for c, *_ in LANGS if c != 'en']


def missing(argv):
    for code in codes(argv):
        gaps = {p: [k for k in load(p, 'en') if k not in load(p, code)] for p in PAGES}
        n = sum(map(len, gaps.values()))
        print(f'{code:8} {n} missing' + ''.join(f'\n    {p}: {len(g)}' for p, g in gaps.items() if g))


def tags_of(s):
    return sorted(re.findall(r'</?[a-zA-Z][^>]*>', s))


def check(argv):
    bad = 0
    for code in codes(argv):
        problems = []
        for p in PAGES:
            en, tr = load(p, 'en'), load(p, code)
            for k, v in en.items():
                if k not in tr:
                    problems.append(f'{p} {k}: missing')
                    continue
                t = tr[k]
                if tags_of(t) != tags_of(v):
                    problems.append(f'{p} {k}: tags differ\n      en: {v[:120]}\n      {code}: {t[:120]}')
                plain = re.sub(r'<[^>]+>|\S+@\S+|Disconnect|Bytehood( Ltd\.?)?|Shuaib Khan|one sec|ScreenZen|Opal|Forest|iPhone|iPad|Android|Mac', ' ', v)
                if t == v and len(re.findall(r'[A-Za-z]{3,}', plain)) >= 2:
                    problems.append(f'{p} {k}: looks untranslated: {v[:80]}')
            extra = set(tr) - set(en)
            if extra:
                problems.append(f'{p}: {len(extra)} stale ids (ok, ignored)')
        hard = [x for x in problems if 'stale' not in x]
        bad += bool(hard)
        print(f'{code}: ' + ('OK' if not hard else f'{len(hard)} problems') +
              ''.join('\n  ' + x for x in problems))
    return bad


def localize(src, page, code, html_lang, folder, label):
    tr_map = load(page, code)

    def tr(text):
        return tr_map.get(sid(text), text)

    src = decorate(src, page, code, label)
    found = list(pieces(src))
    bodies = [(a, b) for a, b, kind, _ in found if kind == 'body']
    edits, nested = {}, {}
    for start, end, kind, text in found:
        if kind == 'ld':
            edits[(start, end)] = 'ld'
        elif kind == 'attr':
            outer = next((b for b in bodies if b[0] <= start and end <= b[1]), None)
            val = tr(text).replace('"', '&quot;')
            if outer:   # attribute on a tag inside a text run: swap it within that run's translation
                nested.setdefault(outer, []).append((src[start:end], val))
            else:
                edits[(start, end)] = val
        else:
            edits[(start, end)] = tr(text)
    for span, swaps in nested.items():
        for raw, val in swaps:
            edits[span] = edits[span].replace(f'="{norm(raw)}"', f'="{val}"', 1)
    out, pos = [], 0
    for (start, end), val in sorted(edits.items()):
        out.append(src[pos:start])
        if val == 'ld':
            data = json.loads(src[start:end])
            ld_apply(data, tr, html_lang)
            val = '\n' + json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        out.append(val)
        pos = end
    out.append(src[pos:])
    s = ''.join(out)
    s = re.sub(r'<html lang="en"', f'<html lang="{html_lang}"', s, count=1)
    own = url_of(page, folder)
    s = re.sub(r'(<link rel="canonical" href=")[^"]*', lambda m: m.group(1) + own, s, count=1)
    s = re.sub(r'(<meta property="og:url"\s+content=")[^"]*', lambda m: m.group(1) + own, s, count=1)
    return s


def render():
    lab = labels()
    for page in PAGES:
        src = open(os.path.join(PUBLIC, page), encoding='utf-8').read()
        done = []
        for code, html_lang, folders, _, _ in LANGS:
            if code == 'en' or not load(page, code):
                continue
            for f in folders:
                out = localize(src, page, code, html_lang, f, lab[code])
                t = os.path.join(PUBLIC, 'localized', f, page)
                os.makedirs(os.path.dirname(t), exist_ok=True)
                open(t, 'w', encoding='utf-8').write(out)
            done.append(code)
        print(f'{page:50} {" ".join(done) or "-"}')


if __name__ == '__main__':
    cmd, *rest = sys.argv[1:] or ['extract']
    if cmd == 'extract':
        extract()
    elif cmd == 'missing':
        missing(rest)
    elif cmd == 'check':
        sys.exit(1 if check(rest) else 0)
    elif cmd == 'render':
        render()
    else:
        sys.exit(__doc__)
