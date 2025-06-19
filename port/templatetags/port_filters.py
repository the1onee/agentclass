from django import template

register = template.Library()

@register.filter
def filter_status(queryset, status):
    return [item for item in queryset if item.status == status]

@register.filter
def mul(value, multiplier):
    """Multiply two numbers"""
    try:
        return float(value) * float(multiplier)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, divisor):
    """Divide two numbers"""
    try:
        divisor = float(divisor)
        if divisor == 0:
            return 0
        return float(value) / divisor
    except (ValueError, TypeError):
        return 0 