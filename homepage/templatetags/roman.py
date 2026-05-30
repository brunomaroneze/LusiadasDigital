from django import template

register = template.Library()

@register.filter
def romano(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value

    romanos = {
        1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
        6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X"
    }
    return romanos.get(value, value)