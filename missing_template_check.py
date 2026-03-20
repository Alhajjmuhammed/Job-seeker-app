import os, re

BASE = r'C:\Users\alhaj\OneDrive\Documents\Projects\Job-seeker-app'
TPL_DIR = os.path.join(BASE, 'templates')
SKIP = ['venv', '__pycache__', '.git', 'node_modules']

template_refs = set()

for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for fname in files:
        if fname.endswith('.py'):
            fpath = os.path.join(root, fname)
            with open(fpath, encoding='utf-8', errors='ignore') as f:
                content = f.read()
            matches = re.findall(r"render\s*\(\s*request\s*,\s*['\"]([^'\"]+)['\"]", content)
            for m in matches:
                template_refs.add(m)

missing = []
for tpl in sorted(template_refs):
    tpl_path = os.path.join(TPL_DIR, tpl.replace('/', os.sep))
    if not os.path.exists(tpl_path):
        missing.append(tpl)

print('=== MISSING TEMPLATES ===')
for m in missing:
    print('  MISSING: ' + m)
print()
print('Total refs scanned: ' + str(len(template_refs)))
print('Total missing: ' + str(len(missing)))
