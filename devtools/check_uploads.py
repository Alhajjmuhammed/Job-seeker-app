#!/usr/bin/env python
"""
File uploads: refuse what is dangerous, accept what the product needs.

Both halves matter. The validator refused every disguised script, but its
"document" category listed only .pdf/.doc/.docx/.txt while the mobile app's
picker offers image/* - so a worker photographing their National ID, which
is how almost all of them do it, had the upload rejected. That blocked
verification, which the whole platform gates on. A validator that is too
strict fails as surely as one that is too loose; this asserts both edges.

    python devtools/check_uploads.py
"""
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
import django  # noqa: E402
django.setup()

from django.core.exceptions import ValidationError  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from workers.file_validators import (  # noqa: E402
    validate_document_file, validate_image_file)

REAL_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE'
    'hQGAhKmMIQAAAABJRU5ErkJggg==')
REAL_PDF = (b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
            b'2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n'
            b'trailer<</Root 1 0 R>>\n%%EOF\n')

ok = fail = 0


def check(label, condition, detail=''):
    global ok, fail
    if condition:
        ok += 1
        print(f'  PASS  {label}')
    else:
        fail += 1
        print(f'  FAIL  {label}   [{detail}]')


def refused(validator, name, data, content_type):
    try:
        validator(SimpleUploadedFile(name, data, content_type=content_type))
        return False
    except Exception:
        return True


def accepted(validator, name, data, content_type):
    try:
        validator(SimpleUploadedFile(name, data, content_type=content_type))
        return True, ''
    except Exception as exc:
        return False, f'{type(exc).__name__}: {exc}'


print()
# --- what must never get through --------------------------------------
check('a PHP script renamed .jpg is refused',
      refused(validate_image_file, 'evil.jpg',
              b'<?php system($_GET["c"]); ?>', 'image/jpeg'))
check('an HTML page renamed .png is refused',
      refused(validate_image_file, 'x.png',
              b'<html><script>alert(1)</script></html>', 'image/png'))
check('an SVG carrying script is refused as an image',
      refused(validate_image_file, 'x.svg',
              b'<svg onload="alert(1)"></svg>', 'image/svg+xml'))
check('an ELF executable renamed .png is refused',
      refused(validate_image_file, 'x.png', b'\x7fELF' + b'\x00' * 64, 'image/png'))
check('a PHP script renamed .pdf is refused as a document',
      refused(validate_document_file, 'cv.pdf', b'<?php echo 1; ?>', 'application/pdf'))
check('plain text renamed .png is refused as a document',
      refused(validate_document_file, 'id.png', b'just text', 'image/png'))
check('a path-traversal filename is refused',
      refused(validate_image_file, '../../etc/passwd.png', b'root:x:0:0', 'image/png'))
check('an oversized file is refused',
      refused(validate_image_file, 'big.png',
              REAL_PNG + b'\x00' * (40 * 1024 * 1024), 'image/png'))

# --- what the product actually needs to work --------------------------
got, why = accepted(validate_image_file, 'photo.png', REAL_PNG, 'image/png')
check('a genuine PNG is accepted as a profile image', got, why)
got, why = accepted(validate_document_file, 'id.png', REAL_PNG, 'image/png')
check('a photographed ID is accepted as a document', got, why)
got, why = accepted(validate_document_file, 'id.pdf', REAL_PDF, 'application/pdf')
check('a scanned PDF is accepted as a document', got, why)

print(f'\n  {ok} passed, {fail} failed\n')
raise SystemExit(1 if fail else 0)
