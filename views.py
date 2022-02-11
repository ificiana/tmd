"""
Module to facilitate integration with django views
"""
from typing import Dict

from django.conf import settings
from django.shortcuts import render as _render
from django.views.generic import TemplateView

from .parse import parse

TMD_DIR = settings.TMD_DIR


class Views(TemplateView):
    """
    Class wrapping TemplateView to help facilitate use of tmd in app/views.py
    """

    def __init__(self, file_location: str, template_location: str = None, **kwargs):
        super().__init__(**kwargs)
        self.location = file_location
        with open(TMD_DIR / self.location, encoding="UTF-8") as file:
            self.tmd = file.read()
        self.context: Dict = {}
        self.context["text"] = parse(self.tmd, self.context)
        self.template_location = template_location or "base/index.html"

    def get(self, request, *args, **kwargs):
        return _render(request, self.template_location, context=self.context)


class Render:
    def __init__(self, file_location, context=None, template_location=None):
        self.location = file_location
        with open(TMD_DIR / self.location, encoding="UTF-8") as file:
            self.tmd = file.read()
        self.context = context or {}
        self.context["text"] = parse(self.tmd, self.context)
        self.template_location = template_location or "base/index.html"

    def __call__(self, request):
        return _render(request, self.template_location, context=self.context)
