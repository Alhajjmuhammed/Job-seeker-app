import struct

def compile_po(po_path, mo_path):
    catalog = {}
    current_msgid = None
    current_msgstr = None
    in_msgid = False
    in_msgstr = False

    with open(po_path, encoding='utf-8') as f:
        lines = f.readlines()

    def unescape(s):
        return s.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')

    for line in lines:
        line = line.rstrip('\n')
        if line.startswith('msgid '):
            if current_msgid is not None and current_msgstr is not None:
                catalog[current_msgid] = current_msgstr
            current_msgid = unescape(line[7:-1])
            current_msgstr = None
            in_msgid = True
            in_msgstr = False
        elif line.startswith('msgstr '):
            current_msgstr = unescape(line[8:-1])
            in_msgid = False
            in_msgstr = True
        elif line.startswith('"') and in_msgid:
            current_msgid += unescape(line[1:-1])
        elif line.startswith('"') and in_msgstr:
            current_msgstr += unescape(line[1:-1])
        elif line == '':
            if current_msgid is not None and current_msgstr is not None:
                catalog[current_msgid] = current_msgstr
            current_msgid = None
            current_msgstr = None
            in_msgid = False
            in_msgstr = False

    if current_msgid is not None and current_msgstr is not None:
        catalog[current_msgid] = current_msgstr

    # Keep the header entry (empty msgid) — gettext reads charset=UTF-8 from it
    # Only filter out non-header entries with empty translations
    catalog = {k: v for k, v in catalog.items() if k == '' or v}

    keys = sorted(catalog.keys())
    ids_bytes = b''.join(k.encode('utf-8') + b'\x00' for k in keys)
    strs_bytes = b''.join(catalog[k].encode('utf-8') + b'\x00' for k in keys)

    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids_bytes)

    koffsets = []
    voffsets = []
    ik = iv = 0
    for k in keys:
        enc_k = k.encode('utf-8')
        enc_v = catalog[k].encode('utf-8')
        koffsets.append((len(enc_k), keystart + ik))
        voffsets.append((len(enc_v), valuestart + iv))
        ik += len(enc_k) + 1
        iv += len(enc_v) + 1

    # MO format requires all key offsets first, then all value offsets (NOT interleaved)
    offsets_data = b''
    for (kl, ko) in koffsets:
        offsets_data += struct.pack('<II', kl, ko)
    for (vl, vo) in voffsets:
        offsets_data += struct.pack('<II', vl, vo)

    header = struct.pack('<IIIIIII',
        0x950412de, 0, len(keys),
        7 * 4, 7 * 4 + 8 * len(keys),
        0, 0
    )

    with open(mo_path, 'wb') as f:
        f.write(header)
        f.write(offsets_data)
        f.write(ids_bytes)
        f.write(strs_bytes)

    print(f'Compiled {po_path} -> {mo_path} ({len(keys)} entries)')


base = r'c:\Users\alhaj\OneDrive\Documents\Projects\Job-seeker-app\locale'
for lang in ['sw', 'fr', 'it']:
    po = fr'{base}\{lang}\LC_MESSAGES\django.po'
    mo = fr'{base}\{lang}\LC_MESSAGES\django.mo'
    compile_po(po, mo)
