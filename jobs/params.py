"""Safe number parameters for list endpoints.

`int(request.query_params.get('limit'))` crashed with a 500 on "abc", and a negative
limit crashed on slicing ("Negative indexing is not supported"). These fall back to the
default and keep the value inside sane bounds instead.
"""


def int_param(params, name, default, lo=1, hi=100):
    try:
        value = int(params.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(value, hi))


def float_param(params, name, default, lo=0.0, hi=1.0):
    try:
        value = float(params.get(name, default))
    except (TypeError, ValueError):
        return default
    if value != value:  # NaN
        return default
    return max(lo, min(value, hi))
