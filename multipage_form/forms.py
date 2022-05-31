from django.forms import modelform_factory
from django.forms.models import ModelForm


class ChildForm(ModelForm):

    required_css_class = 'required'  # used by Django to style required fields
    required_fields = []
    
    class Media:
        css = {
            "all": ("multipage_form/css/multipage_form.css",)
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = self.__class__.__name__
        if self.required_fields == "__all__":
            self.required_fields = self.fields.keys()
        for required_field in self.required_fields:
            field = self.fields.get(required_field)
            if field:
                field.required = True

    # This method can be overridden for forms with branches
    def get_next_form_class(self):
        return getattr(self, "next_form_class", "")


class MultipageForm():

    @classmethod
    def get_child_forms(cls):
        """Return a mapping of child form names to their form classes"""
        child_forms = {}
        for att_name in dir(cls):
            att = getattr(cls, att_name)
            if isinstance(att, type) and issubclass(att, ChildForm):
                # Attach the related model as defined in the subclass
                # of "MultipageForm" to each of the child form classes.
                att._meta.model = cls.model
                # Recreate the class with the model in place. When the
                # class is instantiated, the model will be recognized.
                child_forms[att.__name__] = type(att.__name__, (att,), {"Meta": att._meta})
        return child_forms
