from django import template
from django.template.loader import render_to_string

register = template.Library()

@register.simple_tag(takes_context=True)
def get_history(context):
    form_history = context["form_history"]
    links = []
    for f in form_history:
        links.append(render_to_string("multipage_form/history_link.html", {"f": f}))
    return links
        

@register.inclusion_tag('multipage_form/summary.html', takes_context=True)
def get_form_summary(context):
    form_history = context["form_history"]
    child_form_classes = context["child_forms"]
    instance = context["form"].instance
    sections = []
    for f in form_history:
        child_form_class = child_form_classes[f["name"]]
        fields = []
        for field_name in child_form_class._meta.fields:
            if child_form_class._meta.labels:
                label = child_form_class._meta.labels.get(field_name) or field_name
            else:
                label = field_name
            label = label.replace("_", " ")
            fields.append((label, getattr(instance, field_name, "")))
        sections.append((f["display_name"], fields))
    return { "summary": sections }
