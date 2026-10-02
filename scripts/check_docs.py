#!/usr/bin/env python3
"""Check repository Markdown paths and basic structure without network access."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {'.git', '.venv', 'node_modules', 'target', '.local'}
LINK = re.compile(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)')
FENCE = re.compile(r'^\s*(`{3,}|~{3,})')


def check() -> int:
    errors = []
    documents = 0
    links = 0
    for path in sorted(ROOT.rglob('*.md')):
        if any(part in IGNORED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        documents += 1
        text = path.read_text(encoding='utf-8')
        if not text.strip():
            errors.append(f'{path.relative_to(ROOT)}: empty document')
        fence = None
        for number, line in enumerate(text.splitlines(), 1):
            match = FENCE.match(line)
            if match:
                marker = match.group(1)
                if fence is None:
                    fence = marker
                elif marker[0] == fence[0] and len(marker) >= len(fence):
                    fence = None
                continue
            if fence is not None:
                continue
            for match in LINK.finditer(line):
                target = match.group(1).strip('<>')
                parts = urlsplit(target)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                links += 1
                destination = (path.parent / unquote(parts.path)).resolve()
                if not destination.is_relative_to(ROOT):
                    errors.append(f'{path.relative_to(ROOT)}:{number}: link leaves repository: {target}')
                elif not destination.exists():
                    errors.append(f'{path.relative_to(ROOT)}:{number}: missing path: {target}')
        if fence is not None:
            errors.append(f'{path.relative_to(ROOT)}: unclosed code fence')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Checked {documents} Markdown files and {links} relative links: OK.')
    print('External URLs and heading fragments require separate review. This check does not validate protocol security.')
    return 0


if __name__ == '__main__':
    raise SystemExit(check())
