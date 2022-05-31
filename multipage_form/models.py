from django.db import models


class MultipageModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    is_complete = models.BooleanField(default=False)
    session_key = models.CharField(max_length=32, null=True, unique=True)
