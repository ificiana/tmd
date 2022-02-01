"""
Module to facilitate integration with django views
"""

from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView

from .parse import parse

TMD_DIR = settings.TMD_DIR


class Views(TemplateView):
    def __init__(self, file_location: str, template_location: str = None, **kwargs):
        super().__init__(**kwargs)
        self.location = file_location
        with open(TMD_DIR / self.location) as f:
            self.tmd = f.read()
        self.context = dict()
        self.context["text"] = parse(self.tmd, self.context)
        self.template_location = template_location or "base/index.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_location, context=self.context)
