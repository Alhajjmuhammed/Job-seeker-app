#!/usr/bin/env python
"""
Wrap literal user-facing text in Django templates with {% trans %}.

Deliberately conservative: it only touches text it is certain about, and
leaves anything ambiguous alone for a human. Skipping a string costs a
translation; mangling one breaks the page.

It will wrap:
  - plain text between tags:      <h1>Book a service</h1>
  - a few safe attributes:        placeholder, title, alt, aria-label

It refuses to touch text that:
  - contains {{ }} or {% %}       (already dynamic)
  - sits inside script/style/pre/code/textarea
  - holds a double quote          (would break the {% trans "..." %} literal)
  - has no letters, or is a lone number, symbol or single character
  - is already inside a trans tag

    python devtools/tag_i18n.py --check  templates/accounts/login.html
    python devtools/tag_i18n.py --write  templates/accounts/login.html
"""
import argparse
import pathlib
import re
import sys

SKIP_ELEMENTS = ('script', 'style', 'pre', 'code', 'textarea')
ATTRS = ('placeholder', 'title', 'alt', 'aria-label')

# text sitting between two tags
TEXT_BETWEEN_TAGS = re.compile(r'>([^<>]+)<')
ATTR_PATTERN = re.compile(
    r'\b(' + '|'.join(ATTRS) + r')="([^"{}<>]+)"')
HAS_TEMPLATE_SYNTAX = re.compile(r'\{\{|\{%|\}\}|%\}')
HAS_LETTER = re.compile(r'[A-Za-z]{2}')


def translatable(text):
    """Is this a real sentence a translator should see?"""
    stripped = text.strip()
    if not stripped or len(stripped) < 2:
        return False
    if HAS_TEMPLATE_SYNTAX.search(stripped):
        return False
    if '"' in stripped:
        return False
    if not HAS_LETTER.search(stripped):
        return False
    # A tag cannot span lines: Django will not parse
    #   {% trans "first line
    #             second line" %}
    # and renders it to the page verbatim. Multi-line prose wants
    # {% blocktrans %} and a human deciding where it breaks.
    if '\n' in stripped:
        return False
    # a bare number, a currency amount, an icon name, a css class
    if re.fullmatch(r'[\d\s.,:%+\-/&|()]+', stripped):
        return False
    if re.fullmatch(r'[a-z0-9_\-]+', stripped) and ' ' not in stripped:
        return False  # looks like a slug or identifier, not prose
    return True


def skip_regions(source):
    """Character ranges the tagger must not touch."""
    spans = []
    for element in SKIP_ELEMENTS:
        for m in re.finditer(rf'<{element}\b.*?</{element}>', source,
                             re.S | re.I):
            spans.append((m.start(), m.end()))
    for m in re.finditer(r'\{%\s*(blocktrans|comment).*?\{%\s*end\1\s*%\}',
                         source, re.S):
        spans.append((m.start(), m.end()))
    # Every template tag and variable. A tag like
    #   {% render_field form.email placeholder="Your email" %}
    # carries an attribute that looks exactly like markup, and wrapping it
    # produces a {% trans %} nested inside another tag - which does not parse.
    for m in re.finditer(r'\{%.*?%\}|\{\{.*?\}\}', source, re.S):
        spans.append((m.start(), m.end()))
    return spans


def overlaps(spans, begin, finish):
    """Does [begin, finish) touch any protected region at all?

    Checking only the start point is not enough: a text run can begin outside
    a template tag and extend into one.
    """
    return any(begin < end and start < finish for start, end in spans)


def tag(source):
    """Return (new_source, number_of_strings_wrapped)."""
    spans = skip_regions(source)
    count = 0

    def wrap_text(match):
        nonlocal count
        if overlaps(spans, match.start(), match.end()):
            return match.group(0)
        raw = match.group(1)
        if not translatable(raw):
            return match.group(0)
        leading = raw[:len(raw) - len(raw.lstrip())]
        trailing = raw[len(raw.rstrip()):]
        body = raw.strip()
        count += 1
        return f'>{leading}{{% trans "{body}" %}}{trailing}<'

    result = TEXT_BETWEEN_TAGS.sub(wrap_text, source)

    # The pass above rewrote the string, so every offset in `spans` has
    # shifted. Recompute against the new text before looking at attributes,
    # or the protected regions no longer line up with what they protect.
    spans = skip_regions(result)

    def wrap_attr(match):
        nonlocal count
        if overlaps(spans, match.start(), match.end()):
            return match.group(0)
        name, value = match.group(1), match.group(2)
        if not translatable(value):
            return match.group(0)
        count += 1
        return f'{name}="{{% trans "{value.strip()}" %}}"'

    result = ATTR_PATTERN.sub(wrap_attr, result)

    if count and not re.search(r'\{%\s*load\b[^%]*\bi18n\b', result):
        # {% load %} must follow {% extends %}, which has to come first
        extends = re.search(r'(\{%\s*extends[^%]*%\}\s*\n)', result)
        if extends:
            result = (result[:extends.end()] + '{% load i18n %}\n'
                      + result[extends.end():])
        else:
            result = '{% load i18n %}\n' + result
    return result, count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='+')
    parser.add_argument('--write', action='store_true',
                        help='rewrite the files (default is a dry run)')
    args = parser.parse_args()

    total = 0
    for name in args.paths:
        path = pathlib.Path(name)
        source = path.read_text()
        result, count = tag(source)
        total += count
        state = 'would wrap' if not args.write else 'wrapped'
        print(f'  {state} {count:4} strings  {path}')
        if args.write and count:
            path.write_text(result)
    print(f'  total: {total} strings')
    return 0


if __name__ == '__main__':
    sys.exit(main())
