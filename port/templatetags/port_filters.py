from django import template

register = template.Library()

@register.filter
def filter_status(queryset, status):
    return [item for item in queryset if item.status == status] 