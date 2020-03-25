from django import template
from leidoscloud.models import *

register = template.Library()


# Used to highlight currently active page
@register.simple_tag(takes_context=True)
def current(context, url=None):
    if not "exception" in context and context.request.resolver_match.url_name == url:
        return "active"
    return ""


@register.inclusion_tag("tags/heading_text.html")
def heading_text(current_provider, running_time, end_provider):
    return {
        "current_provider": current_provider,
        "running_time": running_time,
        "end_provider": end_provider,
    }


@register.inclusion_tag("tags/current_status.html")
def current_status():
    return {}


@register.inclusion_tag("tags/nav_link.html")
def nav_link(name, long_name):
    return {"name": name, "long_name": long_name}


@register.inclusion_tag("tags/transition_table.html")
def transition_table():
    # get the fields from the table
    fields = Transition._meta.get_fields()
    names = []
    # for each field, store it's string name in the list which will be passed
    # into the context dictionary for the HTML template
    for f in fields:
        names.append(str(f.name))

    return {
        "headings": names,
        "data": Transition.objects.order_by("-start_time"),
    }


@register.inclusion_tag("tags/predictions_table.html")
def predictions_table():
    # get the fields from the table
    fields = Prediction._meta.get_fields()
    names = []
    # for each field, store it's string name in the list which will be passed
    # into the context dictionary for the HTML template
    for f in fields:
        names.append(str(f.name))

    return {
        "headings": names,
        "data": Prediction.objects.order_by("-time"),
    }
