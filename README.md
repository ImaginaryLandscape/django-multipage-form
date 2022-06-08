# Django Multipage ModelForm

This app helps in the construction of Django model forms that span more
than a single page.


## Features

The "multipage_form" app helps you to separate sections of a long model
form across several pages.  For example, a "job application" form might
have a section where applicants enter their personal information,
another for employment expeience, and so on.

The app allows you to implement different branches or "routes" through
the progression of form pages.  Two users who respond in different ways
on a given page may then be routed to different pages, depending the
values entered.

The app also provides a tool that allows the user to return to a form
page they have already completed, and a related tool that generates a
summary of all completed form pages. These features allow the user to
review and edit their responses before the final submit button is
clicked.


## Requirements

Python 3
Django 3.2


## Example Project

The text below makes reference to an example project that demonstrates
the use of the "multipage_form" app.  That project implements a job
application form, and is available at:

    https://github.com/ImaginaryLandscape/multipage-form-demo


## Installation

- Add this package to your "pyproject.toml" file:

    [tool.poetry.dependencies]
    ...
    multipage-form = {git = "https://github.com/ImaginaryLandscape/django-multipage-form.git", branch = "main"}

 or "requirements.txt":

    -e git+git@github.com:ImaginaryLandscape/django-multipage-form.git@main#egg=multipage_form

- Add it to your "INSTALLED_APPS" in "settings.py":

    INSTALLED_APPS = [
        ...
        'multipage_form'
        ...
    ]

- Run "migrate":

    (virtual_env)$ ./manage.py migrate


## Usage

### The Model

The first step in creating a multipage model form is to create a Django
model for your app. This model should inherit from the `MultipageModel`
class.  This inheritence is necessary because we use sessions to track
which model pertains to which user as the user moves from page to page,
and `MultipageModel` provides a `session_key` field that lets us store a
reference to the session on the relevant model.

The other fields on your model should be -- for the most part -- those
fields that will be populated by user-entered data.  The
"job_application" example project has:


    from django.db import models
    from multipage_form.models import MultipageModel

    class JobApplication(MultipageModel):
        # stage 1 fields
        first_name = models.CharField(max_length=20, blank=True)
        middle_name = models.CharField(max_length=20, blank=True)
        last_name = models.CharField(max_length=20, blank=True)
        # stage 2 fields
        education_level = models.CharField(max_length=20, blank=True)
        year_graduated = models.CharField(max_length=4, blank=True)
        ...


Notice that `blank=True` is passed to all the fields above.  With the
multipage form, it's important to declare your model fields with
`blank=True` for string values or `null=True` for other values.  This is
because unlike with a typical, single-page form, the values on the model
must be saved one chunk at a time, as the user progresses through the
different form pages.  This is true even for fields for which the user
should be required to provide a response.  Therefore, if you want a
given field to be required, it should be done by making the field
required at the form level instead of at the database level.

The "multipage_form" app provides a convenience function to help with
this.  More on that topic below.


### The Form

Once your model is defined, create a "forms.py" module in your app.
Here you should define a "parent form" that inherits from the
`MultipageForm` class.  Inside this parent form, as nested classes, will
be the individual page form classes that define those fields necessary
to populate one "chunk" of the model.  These nested form classes should
inherit from the `ChildForm` class.  The example project has:

    ...
    from multipage_form.forms import MultipageForm, ChildForm
    from .models import JobApplication

    class JobApplicationForm(MultipageForm):
        model = JobApplication
        starting_form = "Stage1Form"

        class Stage1Form(ChildForm):
            next_form_class = "Stage2Form"
            display_name = "Personal Info"
            required_fields = ["first_name", "last_name"]

            class Meta:
                fields = ["first_name", "last_name"]
    ...


Note that the parent form defines two attrbutes. The `model` attribute
points to the model class discussed above, while the value of
`starting_form` matches the name one of the child classes within the
parent class.  This child class will represent the starting point of the
user's progression through the form pages.


#### Form Attributes

##### `next_form_class`

Most of these child classes should define a `next_form_class` attribute,
whose value is the name of the next class in the form progression.  This
must be provided as a string value and should match the name of another
child class within the same parent form.

There are two reasons why a `ChildForm` subclass would *not* define a
`next_form_class` attribute.  If the class represents the last page of
the form, there is no "next" page, and thus no need to provide a
`next_form_class` attribute.

Alternatively, the class might be one for which the next form class
depends on previous user input (a "branching form").  In this case,
instead of a `next_form_class` attribute, you can override the
`get_next_form_class()` method, and determine dynamically what the next
form class should be.  See, for example, `class Stage3Form` in the
"forms.py" module of the example project.


##### `display_name`

The child form can also be given a `display_name` attribute.  This is
the name that will be displayed to the user when using the built-in
history or summary tools. If no `display_name` is defined, the name of
the form class will be used.


##### `required_fields`

We mentioned above that it was important for fields on the model to be
declared as `blank=True` (or `null=True` for non-string fields), because
it is necessary to save instances of the model to the database before
all the fields have been given values.  Unfortunately this means that
fields must be made required at the form level.  To accomplish this in a
normal, single-page form, you would override the form's `__init__()`
method like this:

    class MyForm(ModelForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields["my_field"].required = True

Since the nature of the multipage form might require you to override the
`__init__()` method on most or all of your child forms, the app offers a
convenience feature.  If you define a `required_fields` list on the
child form, the app will automatically make those fields required at the
form level. The value of this field is normally a list of those field
names that should be required in the form.  However, using the string
literal "`__all__`" as the value will cause all fields listed in the
`fields` attribute of the nested `Meta` subclass to be made required.
See, for example, the definition of `class JobApplicationForm` above.


##### Other Configuration

Aside from the special attributes discussed above, you should implement
futher form configuration as you would on a normal Django model form.
This makes sense since the `ChildForm` class is itself a subclass of the
Django model form.  For example, the fields for which each form page is
responsible should be defined in the `fields` attribute of the form
class's neseted `Meta` class, just as they are for regular Django model
forms.  Configuring custom widgets, labels, or help texts are also done
in the `Meta` class.  Examples of all these customizations can be found
in the example project.


### The View

Create a "views.py" module in your app, and define a class-based view
that inherits from the `MultipageFormView` class (which itself is a
subclass of Django's `FormView`).  Beyond that, the view can have a
fairly simple implementation.  The example project has:

    class JobApplicationView(MultipageFormView):
        template_name = 'job_application/job_application.html'
        form_class = JobApplicationForm
        success_url = reverse_lazy("job_application:thank_you")

#### View Attributes

##### `template_name`

As with a normal Django FormView, this defines the template that will be
used to render the form.  Individual form pages can be assigned their
own templates, however, as we will see below.


##### `form_class`

This should point to a subclass of the `MultipageForm` class.


##### `success_url`

The user will be redirected here when no `next_form_class` value is
returned.

##### other configuration

Further customizations should work as with a regular Django FormView.


### The Template

As the user progresses through the multipage form, each individual form
page is made available in the template via the context, just as with a
normal Django form.  A minimal implementation would be:

    <form method="post" action=".">
      {% csrf_token %}
      {{ form.as_p }}
      <button type="submit">Submit</button>
    </form>

If a consistent layout will suffice for all of your individual form
pages, it's enough to just define the `template_name` on the view as
discussed above.

However, if you require more customization for your indivdual form
pages, you may define a `template_name` attribute on the `ChildForm`
subclasses themselves.  In the example project we have:

    class Stage4Form(ChildForm):
        required_fields = "__all__"
        template_name = "job_application/form_page_w_summary.html"

When this form is reached, the form class's `template_name` will
override the `template_name` defined on the view. For `ChildForm`
subclasses that do not define an override, rendering will fall back to
the `template_name` on the view.


### Template Tags / Special Tools

This app provides some template tags that may help the user through the
multipage process.  You can make them available by adding the line

    {% load multipage_form_tags %}

to your template.


#### History

The names of all form pages that the user has completed so far can be
displayed as a series of hyperlinks, allowing the user to jump back and
forth to make further changes.  The example project has:

    {% get_history as links %}
    {% if links %}
    {% for link in links %}
    <ul class="nav">
      <li>{{ link }}</li>
    </ul>
    {% endfor %}
    {% endif %}

Calling the `get_history` tag returns a list of `<span>` elements, each
referencing one form page in the history.  Those referencing forms other
than the one currently on display to the user will also be hyperlinks to
those forms.

Each link in the history chain is rendered in a built-in template.  If
you want to change how the links are rendered, create a path to an
overriding "history_link.html" template in your own app's "templates"
directory.  It should look like:

    <path/to/your/app>/templates/multipage_form/history_link.html


Alternatively, if you want to access the history directly, the list is
available via the `form_history` variable in the context. Each item in
the list has the following properties:

    - `name`: the classname of the form
    - `display_name`: the name as displayed to the user, which may or may not be the same as `name`
    - `page`: the zero-indexed position of each form in the history
    - `is_current`: True if the link represents the form page currently being displayed; False otherwise


#### Link to Previous Form Page

If instead of a complete history you just want to give the user a link
back to the previous form page, a `previous` attribute is included in
the context for all forms other than the starting form.  Its value is
simply the zero-indexed position of the previous form in the
history. You can render such a link in your template like this:

    {% if previous %}
    <a href="?p={{ previous }}">Previous</a>
    {% endif %}


#### Summary of User Input

It may be useful to display to the user a summary of all form responses
before the final "submit" button is clicked.  To accomplish this, you
only need to include:

    {% get_form_summary %}

in your template.

For greater control over the display of the summary, create a path to an
overriding "summary.html" template in your own app's "templates"
directory. It should look like:

    <path/to/your/app>/templates/multipage_form/summary.html

Please refer to the built-in template at

    multipage_form/templates/multipage_form/summary.html

to get an idea of the nature of the summary object.


## Conclusion

The creation and handling of multipage forms is an evergreen problem in
the Django universe.  We hope that this package may speed development in
projects that require such forms.
