from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return {}
    if isinstance(dictionary, dict):
        return dictionary.get(key, {})
    return {}

@register.filter
def get_value(dictionary, key):
    if dictionary is None:
        return 0
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0
