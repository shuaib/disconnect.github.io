#!/usr/bin/env python3
"""Build a legal page in every language from i18n/<page>/<lang>.json + i18n/template.html.

    python3 i18n/render.py privacy terms

English → public/<page>.html (the default). Every other language → public/localized/<folder>/
<page>.html, which Firebase Hosting i18n serves at the same /<page> URL by browser language
(and, for zh-Hant / es-ES, the visitor's country). See "i18n" in firebase.json.
"""
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(HERE, '..', 'public')
PAGE = 'privacy'   # set per page in main()
SITE = 'https://disconnectapp.co'

# (source file, html lang, i18n folders, switcher label, override cookies)
# Hosting drops region subtags from Accept-Language, so regional variants are picked by the
# visitor's country (IP): zh_tw/hk/mo → Traditional, es_es → Spain. The switcher sets Hosting's
# documented override cookies so anyone can pick a language explicitly.
LANGS = [
    ('en',      'en',      [],                        'English',                 ('en', None)),
    ('de',      'de',      ['de'],                    'Deutsch',                 ('de', None)),
    ('fr',      'fr',      ['fr'],                    'Français',                ('fr', None)),
    ('it',      'it',      ['it'],                    'Italiano',                ('it', None)),
    ('pt-BR',   'pt-BR',   ['pt'],                    'Português',               ('pt', None)),
    ('es-MX',   'es-419',  ['es'],                    'Español (Latinoamérica)', ('es', 'mx')),
    ('es-ES',   'es-ES',   ['es_es'],                 'Español (España)',        ('es', 'es')),
    ('nl',      'nl',      ['nl'],                    'Nederlands',              ('nl', None)),
    ('ja',      'ja',      ['ja'],                    '日本語',                   ('ja', None)),
    ('ko',      'ko',      ['ko'],                    '한국어',                   ('ko', None)),
    ('zh-Hans', 'zh-Hans', ['zh'],                    '简体中文',                 ('zh', 'cn')),
    ('zh-Hant', 'zh-Hant', ['zh_tw', 'zh_hk', 'zh_mo'], '繁體中文',               ('zh', 'tw')),
    ('tr',      'tr',      ['tr'],                    'Türkçe',                  ('tr', None)),
    ('pl',      'pl',      ['pl'],                    'Polski',                  ('pl', None)),
    ('ru',      'ru',      ['ru'],                    'Русский',                 ('ru', None)),
]


def url_for(folders):
    return f'{SITE}/{PAGE}' if not folders else f'{SITE}/localized/{folders[0]}/{PAGE}'


def build_main(d, code):
    out = [f'    <h1>{d["h1"]}</h1>',
           f'    <p class="effective-date">{d["effective_date"]}</p>',
           switcher(code)]
    if code != 'en':
        out.append(f'    <p class="translation-note">{d["ui"]["translation_note"]}</p>')
    for b in d['blocks']:
        if 'h2' in b:
            out += ['', '    <hr>', '', f'    <h2>{b["h2"]}</h2>']
        elif 'p' in b:
            out.append(f'    <p>{b["p"]}</p>')
        elif 'ul' in b:
            out.append('    <ul>')
            out += [f'        <li>{li}</li>' for li in b['ul']]
            out.append('    </ul>')
    return '\n'.join(out)


def switcher(code):
    opts = '\n'.join(
        f'        <option value="{c}"{" selected" if c == code else ""}>{label}</option>'
        for c, _, _, label, _ in LANGS)
    label = LABELS[code]
    return (f'    <p class="lang-switch"><label for="langSelect">{label}</label>\n'
            f'      <select id="langSelect">\n{opts}\n      </select></p>')


SWITCHER_SCRIPT = '''<script>
  // Language switcher: sets Firebase Hosting's i18n override cookies, then reloads this page so
  // Hosting serves the chosen language (otherwise it follows the browser language).
  (function () {
    var s = document.getElementById('langSelect');
    if (!s) return;
    var map = %s;
    s.addEventListener('change', function () {
      var o = map[s.value], age = '; path=/; max-age=31536000; SameSite=Lax';
      document.cookie = 'firebase-language-override=' + o[0] + age;
      document.cookie = 'firebase-country-override=' + (o[1] || '') + (o[1] ? age : '; path=/; max-age=0');
      // Pages are browser-cached, and the cache ignores these cookies: refetch first so the
      // navigation gets the newly chosen language, not the copy cached for the old one.
      var target = window.location.pathname.replace(/^\\/localized\\/[^/]+/, '');
      var go = function () { window.location.href = target; };
      fetch(target, { cache: 'reload', credentials: 'same-origin' }).then(go, go);
    });
  })();
</script>'''

STYLE = '''        .lang-switch { margin: -32px 0 32px; font-size: 14px; color: rgba(60, 55, 50, 0.60); }
        .lang-switch label { margin-right: 8px; }
        .lang-switch select { font: inherit; color: #3C3732; background: transparent; border: 0.5px solid rgba(11, 11, 12, 0.2); border-radius: 8px; padding: 4px 8px; }
        .translation-note { font-size: 14px; color: rgba(60, 55, 50, 0.60); font-style: italic; }
'''

LABELS = {}


def render(code, d, tpl):
    entry = next(e for e in LANGS if e[0] == code)
    _, html_lang, folders, _, _ = entry
    url = url_for(folders)
    alternates = [f'<link rel="alternate" hreflang="{e[1]}" href="{url_for(e[2])}">' for e in LANGS]
    alternates.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}/{PAGE}">')
    s = tpl
    s = s.replace('{{lang}}', html_lang).replace('{{url}}', url).replace('{{hreflang}}', '\n'.join(alternates))
    for k, v in d['ui'].items():
        s = s.replace('{{ui.%s}}' % k, html.escape(v, quote=True) if k in ('meta_description', 'page_title') else v)
    s = s.replace('{{main}}', build_main(d, code)).replace('{{h1}}', d['h1'])
    s = s.replace('{{switcher_script}}', SWITCHER_SCRIPT % json.dumps({e[0]: list(e[4]) for e in LANGS}))
    s = s.replace('{{page}}', PAGE)
    s = s.replace('    </style>', STYLE + '    </style>', 1)
    left = re.findall(r'\{\{[a-z0-9_.]+\}\}', s)
    assert not left, (code, left)
    return s, folders


def main(pages):
    global PAGE
    tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    for page in pages:
        PAGE = page
        src = os.path.join(HERE, page)
        LABELS.clear()
        for code, *_ in LANGS:
            path = os.path.join(src, f'{code}.json')
            if os.path.exists(path):
                LABELS[code] = json.load(open(path, encoding='utf-8'))['ui']['language_label']
        done = []
        for code, *_ in LANGS:
            path = os.path.join(src, f'{code}.json')
            if not os.path.exists(path):
                print(f'{page}: skip {code} (no {code}.json)')
                continue
            d = json.load(open(path, encoding='utf-8'))
            html_page, folders = render(code, d, tpl)
            targets = [os.path.join(PUBLIC, f'{page}.html')] if not folders else \
                      [os.path.join(PUBLIC, 'localized', f, f'{page}.html') for f in folders]
            for t in targets:
                os.makedirs(os.path.dirname(t), exist_ok=True)
                open(t, 'w', encoding='utf-8').write(html_page)
            done.append(code)
        print(f'{page}: rendered', ', '.join(done))


if __name__ == '__main__':
    import sys
    main(sys.argv[1:] or ['privacy', 'terms'])
