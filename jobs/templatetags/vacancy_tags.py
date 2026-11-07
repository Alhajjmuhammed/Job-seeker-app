from django import template

register = template.Library()


@register.filter
def tsh(value):
    """250000 -> "250,000" in every language (Swahili pages had no separators)."""
    try:
        return f'{int(round(float(value))):,}'
    except (TypeError, ValueError):
        return value
