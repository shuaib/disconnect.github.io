# Translating the Disconnect privacy policy — agent brief

Translate `/Users/shuaibkhan/workspace/disconnect.github.io/i18n/<page>/en.json` into your
assigned languages. Write one file per language next to it: `<code>.json` (codes below), with
EXACTLY the same structure: same keys, same number and order of blocks and list items. Then run
`python3 /Users/shuaibkhan/workspace/disconnect.github.io/i18n/privacy/check.py <page> <code>` until it
says OK. Do not edit any other file. Do not deploy anything.

## What this is
A legal privacy policy for an iOS app, written to be warm and plain-spoken. Keep it accurate —
don't add, drop or soften any commitment — but natural, not stiff legalese. Same meaning,
sentence by sentence.

## Hard rules
- Keep every HTML tag, attribute and href exactly (`<strong>`, `<br>`, `<a href="…" target="_blank" rel="noopener">`).
  Only the visible text changes. Don't translate email addresses, URLs or ico.org.uk.
- Keep names as-is: Disconnect, Disconnect Pro, Pro, Bytehood Ltd, Google Firebase, RevenueCat,
  PostHog, Resend, Apple, App Store, disconnectapp.co, ICO.
- Apple features use Apple's OWN official name in that language:
  "Sign in with Apple" and "Hide My Email" (e.g. de: "Mit Apple anmelden", "E-Mail-Adresse verbergen";
  fr: "Se connecter avec Apple", "Masquer mon adresse e-mail"; ja: "Appleでサインイン", "メールを非公開").
  If unsure, use the wording Apple uses in iOS Settings in that language.
- The in-app path "Settings → Delete account" must use the app's own translations of those two
  labels. Look them up in `/Users/shuaibkhan/workspace/ios/disconnect/disconnect/Localizable.xcstrings`
  (keys "Settings" and "Delete account", your Xcode language — see table) and use them verbatim.
- Use the app's terms from `/Users/shuaibkhan/workspace/ios/disconnect/.l10n-work/glossary_<xcode>.md`:
  the buddy word (e.g. es-ES "colega", ja "バディ", ko "지킴이", zh "伙伴/夥伴", tr "destekçi",
  pl "kumpel", ru "друг"), "rule", and the register (du/vous/tú/…). Use the same register as the app.
- Legal terms: use the standard term in that language for "standard contractual clauses"
  (EU SCCs), "legitimate interest", "legal basis", "data protection authority".
- "Effective date: 28 October 2026" — translate and format the date the normal way for that language.
- `ui.translation_note` must say: this is a translation of the English policy; if they differ,
  the English version applies.
- `ui.language_label` is the label for the language picker ("Language").
- Nav/footer labels (ui.*) are short website menu items — translate naturally ("FAQ" may stay "FAQ"
  where that's normal).
- Typography: ja/zh full-width punctuation, 「」 quotes in ja/zh-Hant, “” in zh-Hans; fr non-breaking
  space before : ; ! ? and inside « »; de „…“; pl „…”; ru «…».

## Codes
| file code | Xcode language (glossary + xcstrings) |
|---|---|
| de | de | | fr | fr | | it | it | | pt-BR | pt-BR | | es-MX | es-MX | | es-ES | es |
| nl | nl | | ja | ja | | ko | ko | | zh-Hans | zh-Hans | | zh-Hant | zh-Hant |
| tr | tr | | pl | pl | | ru | ru |

es-MX is Latin American Spanish (tú, "buddy" per its glossary); es-ES is Spain Spanish (tú, "colega").
zh-Hant is Taiwan usage.

## Report back (short)
Per language: file written + check OK, the buddy word and register used, and any sentence you
weren't sure about.

## Terms of Service (page "terms")
Same rules, applied to `i18n/terms/en.json` → `i18n/terms/<code>.json`; check with
`python3 i18n/check.py terms <code>`. For consistency, reuse the wording your language already uses
in `i18n/privacy/<code>.json` for shared items (ui labels, buddy word, "Settings → Delete account",
Privacy Policy title — the `<a href="/privacy">` link text should be that page's h1).
Terms-specific:
- Keep section numbers ("1." … "13.") and "£50" exactly.
- Use the established legal terms in your language for: statutory rights, consumer, third-party
  beneficiaries, governing law, the courts of England and Wales, negligence, personal injury.
- "Apple's standard Licensed Application End User License Agreement" — use Apple's own name for it in
  your language if one exists (it's Apple's "Standard EULA"); otherwise translate it plainly.
- Keep it as friendly and plain as the English — this is deliberately not heavy legalese.
