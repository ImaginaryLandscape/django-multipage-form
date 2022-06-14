import datetime, pytz
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.decorators import classonlymethod
from django.utils.text import camel_case_to_spaces
from django.views.generic import FormView
from .forms import MultipageForm, ChildForm

# Error messages for assertions
NO_FORM_CLASS = "Subclasses of 'MultipageFormView' must declare a 'form_class'"
BAD_FORM_CLASS = "The 'form_class' of a subclass of 'MultipageFormView' must be a class"
NO_STARTING_FORM = "Subclasses of 'MultipageForm' must declare a 'starting_form'"
NO_MATCHING_FORM = "The value of 'starting_form' must match one of the MultipageForm's child classes"

max_age = getattr(settings, "MULTIPAGE_FORM_SESSION_TIMEOUT", 600)


class MultipageFormView(FormView):
    mp_form_class = ""              # must be overridden in subclass (as "form_class")
    success_url = ""                # may be overridden in subclass
    template_name = ""              # must be overridden in subclass
    child_forms = {}                # will be populated automatically
    starting_form_class_name = ""   # will be populated automatically

    @classonlymethod
    def as_view(cls, **initkwargs):
        mp_form_class = getattr(cls, "form_class", None)
        assert mp_form_class, NO_FORM_CLASS
        assert isinstance(mp_form_class, type), BAD_FORM_CLASS
        assert getattr(mp_form_class, "starting_form", None), NO_STARTING_FORM
        child_forms = mp_form_class.get_child_forms()
        assert any([ cf for cf in child_forms if cf == mp_form_class.starting_form]), NO_MATCHING_FORM
        # "child_forms" will be a mapping of class names to classes
        initkwargs["child_forms"] = child_forms
        initkwargs["mp_form_class"] = mp_form_class
        initkwargs["starting_form_class_name"] = mp_form_class.starting_form
        return super().as_view(**initkwargs)
                
    def dispatch(self, request, *args, **kwargs):
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        # Get the instance for this session, if there is one.
        self.instance = self.get_instance_from_key(session_key)
        if self.instance:
            p = request.GET.get("p", "")
            p = int(p) if p.isnumeric() else None
            if p is not None and p <= len(request.session["history"]):
                request.session["history_pointer"] = p

            if self.instance.is_expired:
                self.instance.delete()
                messages.info(
                    request,
                    "Your time to complete this form has expired. Please restart from the beginning."
                )
                # Start the user over.
                return redirect(request.path_info)
        else:
            # This is a new form, so initialize these session values.
            request.session["history"] = []
            request.session["history_pointer"] = 0
            if request.method == "POST":
                self.instance = self.mp_form_class.model(session_key=session_key)

        self.history = request.session["history"]
        self.history_pointer = request.session["history_pointer"]

        # The history pointer points to the *next* point of insertion in the
        # history.  So normally it will point to an index that doesn't exist
        # yet. For example, the user starts with an empty history list and a
        # history pointer of 0.  But if the user goes back into the history,
        # there will be a form class at that index. In that scenario, return
        # that form class.
        if len(self.history) > self.history_pointer:
            self.form_class = self.child_forms[self.history[self.history_pointer]]
        # This is a new form, so use "starting_form_class_name".
        elif self.history_pointer == 0:
            self.form_class = self.child_forms[self.starting_form_class_name]
        # The user has passed the starting form and needs the next class.
        else:
            self.form_class = self.child_forms[self.request.session.get("next_form_class")]

        # If this form class has its own template, override the default.
        if getattr(self.form_class, "template_name", None):
            self.template_name = self.form_class.template_name
        
        return super().dispatch(request, *args, **kwargs)

    def check_future_history(self, next_form_class, instance):
        lookahead_pointer = self.history_pointer
        next_form_class = self.child_forms[next_form_class]
        while len(self.history) > lookahead_pointer:
            if next_form_class.__name__ == self.history[lookahead_pointer]:
                # The next class in the future history is the same as "next_Form_class".
                # That means we have not diverged onto another branch. To keep looking
                # farther ahead, we now instantiate "next_form_class". We must do this
                # because the next form class may depend on values set in the instance.
                next_form_instance = next_form_class(data=instance, instance=instance)
                # Now examine *that* instance's "next_form_class"
                next_form_class = self.child_forms[next_form_instance.get_next_form_class()]
                lookahead_pointer += 1
            else:
                # The user has made a change that changes the branching, so drop any
                # child forms that don't apply to the new route.
                self.history.pop(lookahead_pointer)
        
    def form_valid(self, form):
        next_form_class = form.get_next_form_class()
        if next_form_class == "":
            form.instance.is_complete = True
            form.instance.session_key = None
            # force an end to this session; see
            # https://github.com/django/django/blob/1.8.2/django/contrib/sessions/backends/base.py#L297
            self.request.session.create()
            next_page = self.get_success_url()
        else:
            if len(self.history) == self.history_pointer:
                # Add the form that's just been declared valid to the history.
                self.history.append(form.__class__.__name__)
            self.history_pointer += 1

            # Now look ahead to see if we need to dump any "future history".
            self.check_future_history(next_form_class, form.instance)
            
            # Note: No need to resave the history to the session since lists are
            # passed by reference, but we do need to resave "history_pointer".
            self.request.session["history_pointer"] = self.history_pointer
            self.request.session["next_form_class"] = next_form_class

            next_page = self.request.path_info

        form.save()  # This will save the underlying model instance.
        return redirect(next_page)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["child_forms"] = self.child_forms
        context_data["form_history"] = self.get_history_for_template()
        if self.history_pointer > 0:
            # convert page number to string so "{% if previous %}"
            # will work in template even when "previous" is zero.
            context_data["previous"] = str(self.history_pointer - 1)
        return context_data

    def get_display_name_from_name(self, name):
        # If the form class name is camel case, convert to spaces
        name = camel_case_to_spaces(name)
        # If the form class name has underscores, the operation
        # above may have introduced sequences of "_ "
        name = name.replace("_ ", " ").replace("_", " ")
        # Make the first character a captial
        return name.title()

    def get_history_for_template(self):
        history = []
        for i in range(len(self.history)):
            form_class_name = self.history[i]
            form_class = self.child_forms[form_class_name]
            display_name = getattr(
                form_class,
                "display_name",
                self.get_display_name_from_name(form_class_name)
            )
            history.append({
                "name": form_class_name,
                "display_name": display_name,
                "page": i,
                "is_current": i == self.history_pointer
            })
        return history

    def get_instance_from_key(self, session_key):
        # Find and return an unexpired, not-yet-completed model instance
        # with a matching session_key, or None if no such object exists.
        try:
            instance = self.mp_form_class.model.objects.get(session_key=session_key)
        except self.mp_form_class.model.DoesNotExist:
            return None
        # else
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        instance.is_expired = instance.modified < now - datetime.timedelta(seconds=max_age)
        return instance

    def get_form_kwargs(self):
        # Make sure Django uses the same model instance we've already been
        # workin on, or it will instantiate a new one after every submit.
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        # User can provide a "success_url" for when all pages of the form
        # are complete. If they don't, return to the beginning of the process.
        return self.success_url or self.request.path_info
