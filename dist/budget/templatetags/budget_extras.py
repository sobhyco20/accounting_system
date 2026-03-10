from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0



# ✅ تعديل اسم الفلتر لتفادي التعارض
@register.filter(name='get_attr')
def get_attr(obj, attr_name):
    return getattr(obj, attr_name, 0)


@register.filter
def get_actual(entry, month):
    if hasattr(entry, 'actual') and entry.actual:
        return getattr(entry.actual, month, 0)
    return 0

@register.filter
def get_months(entry):
    return ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']

@register.filter
def variance(actual, estimated):
    try:
        return (actual or 0) - (estimated or 0)
    except:
        return 0


@register.filter
def dict_get(d, key):
    if isinstance(d, dict):
        return d.get(key, 0)
    return 0


@register.filter
def bg_color(level):
    return {
        1: '#dfe6e9',
        2: '#d0ebff',
        3: '#d3f9d8',
        4: '#fff3cf',
    }.get(level, '#ffffff')




@register.filter
def get_estimate(entry, month):
    # تأكد أن month نص وليس tuple
    if isinstance(month, tuple):
        month = month[0]
    return getattr(entry, month, 0)

@register.filter
def get_total_estimate(entry):
    return entry.total()