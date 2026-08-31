#!/usr/bin/env python
"""
Static audit for the kinds of defect this codebase has actually shipped.

Every check here exists because the corresponding bug reached production at
least once. None of them need a database or a running server - they read the
source and compare it against the real models, so they are fast enough to run
before every deploy.

    python devtools/audit.py

Exits non-zero if anything is found, so it can gate a deploy script.
"""
import ast
import os
import pathlib
import sys

# Python puts this script's own directory on sys.path, not the working
# directory, so the project root has to be added explicitly for
# `python devtools/audit.py` to find the apps.
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import django  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.apps import apps  # noqa: E402
from django.core.exceptions import FieldDoesNotExist  # noqa: E402

SKIP_PARTS = ('.venv', 'migrations', 'node_modules', 'devscripts', '__pycache__')

MODELS = {m.__name__: m for m in apps.get_models()}

# Known and deliberately accepted. Each entry needs a reason, and should be
# removed rather than added to whenever the underlying situation is resolved.
ACCEPTED = {
    # Document expiry is written against a WorkerDocument.expiry_date column
    # that does not exist yet. Nothing calls it, and both entry points return
    # early when the field is absent, so it cannot raise - but the source
    # still names the field, which this static check correctly sees.
    ('worker_connect/document_verification.py', 'expiry_date__lt'),
    ('worker_connect/document_verification.py', 'expiry_date__lte'),
    ('worker_connect/document_verification.py', 'expiry_date__gte'),
}
LOOKUPS = {
    'exact', 'iexact', 'contains', 'icontains', 'in', 'gt', 'gte', 'lt', 'lte',
    'startswith', 'istartswith', 'endswith', 'iendswith', 'range', 'date',
    'year', 'month', 'day', 'week', 'week_day', 'quarter', 'time', 'hour',
    'minute', 'second', 'isnull', 'regex', 'iregex', 'unaccented', 'search',
}
# Only methods whose arguments must name a real field on the model.
# annotate()/aggregate() *define* aliases rather than reference fields, and
# order_by()/values() may legitimately use those aliases, so including any of
# them produces noise rather than findings.
QUERY_METHODS = {
    'filter', 'exclude', 'get', 'select_related', 'prefetch_related',
}


def source_files():
    for path in ROOT.rglob('*.py'):
        sp = str(path)
        if any(part in sp for part in SKIP_PARTS):
            continue
        if sp.endswith('devtools/audit.py'):
            continue
        yield path


def resolve_path(model, dotted):
    """Walk a Django field path like 'service_request__client__email'."""
    parts = [p for p in dotted.split('__') if p]
    current = model
    for i, part in enumerate(parts):
        if part in LOOKUPS and i == len(parts) - 1:
            return True
        if part == 'pk':
            continue
        try:
            field = current._meta.get_field(part)
        except (FieldDoesNotExist, AttributeError):
            return False
        related = getattr(field, 'related_model', None)
        if related is not None:
            current = related
        elif i != len(parts) - 1:
            nxt = parts[i + 1]
            return nxt in LOOKUPS
    return True


def check_field_paths():
    """Querysets that name a field the model does not have (raises FieldError)."""
    findings = []
    for path in source_files():
        try:
            tree = ast.parse(path.read_text(errors='ignore'))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not (isinstance(fn, ast.Attribute) and fn.attr in QUERY_METHODS):
                continue
            # Find the model name at the root of the chain: Model.objects.filter(...)
            cur, model_name = fn.value, None
            while isinstance(cur, ast.Call):
                cur = cur.func.value if isinstance(cur.func, ast.Attribute) else None
                if cur is None:
                    break
            while isinstance(cur, ast.Attribute):
                if cur.attr == 'objects' and isinstance(cur.value, ast.Name):
                    model_name = cur.value.id
                    break
                cur = cur.value
            model = MODELS.get(model_name) if model_name else None
            if model is None:
                continue
            names = [k.arg for k in node.keywords if k.arg]
            names += [a.value.lstrip('-') for a in node.args
                      if isinstance(a, ast.Constant) and isinstance(a.value, str)]
            rel = str(path.relative_to(ROOT))
            for name in names:
                if (rel, name) in ACCEPTED:
                    continue
                if not resolve_path(model, name):
                    findings.append(
                        (rel, node.lineno,
                         f'{model_name}.objects.{fn.attr}({name!r})'))
    return findings


def check_null_into_not_null():
    """create() passing None into a column the database declares NOT NULL."""
    findings = []
    for path in source_files():
        try:
            tree = ast.parse(path.read_text(errors='ignore'))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not (isinstance(fn, ast.Attribute) and fn.attr in ('create', 'get_or_create')):
                continue
            inner = fn.value
            if not (isinstance(inner, ast.Attribute) and inner.attr == 'objects'):
                continue
            if not isinstance(inner.value, ast.Name):
                continue
            model = MODELS.get(inner.value.id)
            if model is None:
                continue
            for kw in node.keywords:
                if kw.arg is None:
                    continue
                value, risky = kw.value, False
                if isinstance(value, ast.IfExp):
                    for branch in (value.body, value.orelse):
                        if isinstance(branch, ast.Constant) and branch.value is None:
                            risky = True
                if isinstance(value, ast.Constant) and value.value is None:
                    risky = True
                if not risky:
                    continue
                try:
                    field = model._meta.get_field(kw.arg)
                except FieldDoesNotExist:
                    continue
                if not getattr(field, 'null', True):
                    findings.append(
                        (str(path.relative_to(ROOT)), node.lineno,
                         f'{inner.value.id}.{kw.arg} is NOT NULL but may receive None'))
    return findings


def check_serializers():
    """ModelSerializers that cannot even be built (a 500 on first use)."""
    import importlib
    import inspect
    from rest_framework import serializers as drf

    findings, seen = [], set()
    for path in ROOT.rglob('*serializer*.py'):
        sp = str(path)
        if any(part in sp for part in SKIP_PARTS):
            continue
        module = sp[len(str(ROOT)) + 1:-3].replace('/', '.')
        try:
            mod = importlib.import_module(module)
        except Exception:
            continue
        for name, obj in vars(mod).items():
            if not (inspect.isclass(obj) and issubclass(obj, drf.Serializer)):
                continue
            if obj.__module__ != module or (module, name) in seen:
                continue
            seen.add((module, name))
            if getattr(getattr(obj, 'Meta', None), 'model', None) is None:
                continue
            try:
                obj().fields
            except Exception as exc:
                findings.append((module, name, str(exc)[:150]))
    return findings


def check_templates():
    """Templates a routed view renders that do not exist (a 500 on open)."""
    import re
    from django.template import TemplateDoesNotExist
    from django.template.loader import get_template

    pattern = re.compile(
        r"""render\(\s*request\s*,\s*['"]([^'"]+\.html)['"]"""
        r"""|template_name\s*=\s*['"]([^'"]+\.html)['"]""")
    findings = []
    for path in source_files():
        for m in pattern.finditer(path.read_text(errors='ignore')):
            name = m.group(1) or m.group(2)
            try:
                get_template(name)
            except TemplateDoesNotExist:
                findings.append((str(path.relative_to(ROOT)), name))
    return findings


def check_unbound_names():
    """Names used but never imported or assigned (a NameError at runtime)."""
    import builtins
    findings = []
    for path in source_files():
        try:
            tree = ast.parse(path.read_text(errors='ignore'))
        except SyntaxError as exc:
            findings.append((str(path.relative_to(ROOT)), f'SyntaxError: {exc}'))
            continue
        if any(isinstance(n, ast.ImportFrom) and n.names and n.names[0].name == '*'
               for n in ast.walk(tree)):
            continue  # star-import; cannot know what it brought in
        bound = set()

        class Collect(ast.NodeVisitor):
            def visit_Import(self, n):
                for a in n.names:
                    bound.add((a.asname or a.name).split('.')[0])

            def visit_ImportFrom(self, n):
                for a in n.names:
                    bound.add(a.asname or a.name)

            def visit_FunctionDef(self, n):
                bound.add(n.name); self.generic_visit(n)

            def visit_AsyncFunctionDef(self, n):
                bound.add(n.name); self.generic_visit(n)

            def visit_ClassDef(self, n):
                bound.add(n.name); self.generic_visit(n)

            def visit_Name(self, n):
                if isinstance(n.ctx, (ast.Store, ast.Del)):
                    bound.add(n.id)
                self.generic_visit(n)

            def visit_arg(self, n):
                bound.add(n.arg); self.generic_visit(n)

            def visit_ExceptHandler(self, n):
                if n.name:
                    bound.add(n.name)
                self.generic_visit(n)

            def visit_Global(self, n):
                bound.update(n.names)

        Collect().visit(tree)
        used = {n.id for n in ast.walk(tree)
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        missing = used - bound - set(dir(builtins)) - {
            '__file__', '__name__', '__doc__', 'self', 'cls'}
        if missing:
            findings.append((str(path.relative_to(ROOT)), ', '.join(sorted(missing))))
    return findings


CHECKS = (
    ('queryset field paths that do not exist', check_field_paths),
    ('None passed into a NOT NULL column', check_null_into_not_null),
    ('serializers that cannot be built', check_serializers),
    ('templates a view renders but that are missing', check_templates),
    ('names used but never bound', check_unbound_names),
)


def main():
    total = 0
    for title, fn in CHECKS:
        findings = fn()
        total += len(findings)
        mark = 'ok  ' if not findings else 'FAIL'
        print(f'  [{mark}] {title}: {len(findings)}')
        for finding in findings:
            print('           ' + '  '.join(str(p) for p in finding))
    print(f'\n  total findings: {total}')
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
