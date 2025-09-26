from django import template

register = template.Library()



@register.filter
def divide(value, arg):
    """Divide value by arg safely."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0


# @register.filter
# def get_item(dictionary, key):
#     """Get a value from a dictionary by key"""
#     return dictionary.get(key, "")
@register.filter
def percentage(part, total):
    try:
        return (float(part) / float(total)) * 100
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def sum_attr(queryset, attr):
    return sum(getattr(item, attr, 0) for item in queryset)


@register.filter
def dict_get(d, key):
    """Get dictionary value by key in templates."""
    if d and key in d:
        return d.get(key, "")
    return ""

@register.filter
def underscore_to_space(value):
    """Replace underscores with spaces in a string"""
    return value.replace('_', ' ')

@register.filter
def underscore_to_space(value):
    """Replaces underscores with spaces"""
    return str(value).replace("_", " ")

@register.filter
def get_item(dictionary, key):
    """Access dictionary item by key in template"""
    return dictionary.get(key, "")

@register.filter
def sum_attr(queryset, attr):
    return sum(getattr(item, attr, 0) for item in queryset)

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divided_by(value, arg):
    """Divide the value by the argument."""
    try:
        arg = float(arg)
        if arg == 0:
            return 0
        return float(value) / arg
    except (ValueError, TypeError):
        return 0
    
@register.filter
def currency(value):
    """Format a number as currency with ₹ symbol"""
    try:
        value = float(value)
        return f"₹{value:,.2f}"
    except (ValueError, TypeError):
        return value    
    
@register.filter
def format_inr(value):
    """
    Format a number into Indian Rupee format (with commas).
    Example: 1234567 -> 12,34,567
    """
    try:
        value = float(value)
        return "₹{:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value