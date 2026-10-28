#!/usr/bin/env python3
"""Check translations against English: check.py <page> <code> [<code>...]"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = re.compile(r'<[^>]+>')
LINKS = re.compile(r'href="[^"]*"|mailto:[^"<\s]+|https?://[^"<\s]+')


def walk(a, b, path, errs):
    if isinstance(a, dict):
        if not isinstance(b, dict) or set(a) != set(b):
            errs.append(f'{path}: keys differ ({sorted(set(a) ^ set(b if isinstance(b, dict) else {}))})')
            return
        for k in a:
            walk(a[k], b[k], f'{path}.{k}', errs)
    elif isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            errs.append(f'{path}: list length {len(a)} vs {len(b) if isinstance(b, list) else "?"}')
            return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f'{path}[{i}]', errs)
    elif isinstance(a, str):
        if not isinstance(b, str) or not b.strip():
            errs.append(f'{path}: missing translation')
            return
        if sorted(TAG.findall(a)) != sorted(TAG.findall(b)):
            errs.append(f'{path}: HTML tags differ')
        if sorted(LINKS.findall(a)) != sorted(LINKS.findall(b)):
            errs.append(f'{path}: links/emails differ')
        # Text left after removing tags, links and fixed names — if nothing remains, there's
        # nothing to translate (e.g. the contact block), so identical is correct.
        rest = re.sub(r'Bytehood Ltd|Disconnect Pro|Disconnect|Google Firebase|RevenueCat|PostHog|Resend|Apple|ICO', '',
                      re.sub(r'\S+@\S+', '', LINKS.sub(' ', TAG.sub(' ', a))))
        if a.strip() == b.strip() and len(re.sub(r'[\W_]+', '', rest)) > 3 and not path.startswith('root.ui.'):
            errs.append(f'{path}: looks untranslated')


PAGE = sys.argv[1]
en = json.load(open(os.path.join(HERE, PAGE, 'en.json'), encoding='utf-8'))
ok = True
for code in sys.argv[2:]:
    try:
        d = json.load(open(os.path.join(HERE, PAGE, f'{code}.json'), encoding='utf-8'))
    except Exception as e:
        print(f'{code}: cannot read — {e}'); ok = False; continue
    errs = []
    walk({k: v for k, v in en.items() if k != '_notes'}, {k: v for k, v in d.items() if k != '_notes'}, 'root', errs)
    print(f'{code}: ' + ('OK' if not errs else 'FAIL\n  ' + '\n  '.join(errs[:20])))
    ok = ok and not errs
sys.exit(0 if ok else 1)
