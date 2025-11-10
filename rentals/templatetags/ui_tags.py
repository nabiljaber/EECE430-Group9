from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    """Return d[key] for dict-like objects in templates."""
    try:
        return d.get(key)
    except Exception:
        return None

