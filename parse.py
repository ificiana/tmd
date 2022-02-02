"""
Implements the parser
"""

import re
from typing import Callable, Union

from django.template import Template, Context
from django.template.defaultfilters import linebreaks, register
from django.template.exceptions import (TemplateSyntaxError,
                                        TemplateDoesNotExist)

from .exec import _exec, _infer

# regex patterns for context inference
RE_LIST = re.compile(r"(\w+?):\s*list\n*\s*=>\s*(.*)\s*\n")
RE_DICT = re.compile(r"(\w+?):\s*dict\n*\s*=>\s*\[(.*)]\s*\n")
RE_STR = re.compile(r"(\w+?):\s*str\n*\s*=>\s*(.*)\s*\n")
# Todo: make RE_STR such that it allows default to be str
# regex pattern for filters declaration
RE_FN = re.compile(r"(.*)?\((.*?)\)\s*<=\s*(.*?)$")


class TMDExtract:
    """
    Class for text extracted from tmd file
    """

    def __init__(self, _text):
        self.text = _text
    # Todo: implement sanitisation

    def sanitise(self):
        """
        Sanitise input for safer execution
        """
        return self.text


class Parse:
    """
    Parser class
    """

    def __init__(self, text):
        self.raw = text
        self.tmd_context = None
        self.body = None
        self.final = None
        self.filters = []

    @staticmethod
    def _modify(_text: str, _d: dict[str, str]) -> str:
        """
        Helper function to bulk modify a string
        :param _text: the string to modify
        :param _d: dictionary of match and replacement expressions
        :return: returns the modified text
        """
        for _k, _v in _d.items():
            _text = re.compile(_k).sub(_v, _text)
        return _text

    @staticmethod
    def _infer_helper(_tmd_context: str, _context: dict) -> dict:
        """
        Intermediate function to help infer context from a tmd file
        :param _tmd_context: string extracted from within -[context]
        :param _context: passed in context from views.py
        :return: updated context dict
        """
        # Todo: support multiline declarations
        lists = RE_LIST.findall(_tmd_context)
        dicts = RE_DICT.findall(_tmd_context)
        strs = RE_STR.findall(_tmd_context)
        _body = ""
        for i in lists:
            _body += f"{i[0]} = {i[1]}\n"
        for i in dicts:
            _body += f"{i[0]} = {{{i[1]}}}\n"
        for i in strs:
            _body += f"{i[0]} = {i[1]}\n"
        return _context | _infer(_body, _context)

    def _exec_helper(self, _fn: str) -> Union[Callable, None]:
        """
        Intermediate function to help compile filter functions
            extracted from a tmd file
        :param _fn: filter declaration extracted from within -[filters]
        :return: a function object
        """
        _fn = RE_FN.match(_fn.strip())
        # ignore wrong syntax
        if not _fn:
            return None
        _def = _fn[1].strip()
        if _def.startswith("_"):
            return err(TemplateSyntaxError,
                       "Filter names can not begin with '_'")
        # Todo: better error handling
        _args = [_i.strip() for _i in _fn[2].split(",")]
        _body = self._modify(_fn[3].strip(), {
            rf"\b{_args[0]}\b": "a",
            rf"\b{_args[1]}\b" if len(_args) == 2 else "===": "b",
        })
        _body = f"def {_def}(a, b=None): return {_body}"
        return _exec(_body, _def)

    def _register(self, _fn_list: list) -> None:
        """
        Internal function to register filter functions with django
        :param _fn_list: lines split from string extracted from within -[filters]
        """
        for _fn in _fn_list:
            if (_fn_obj := self._exec_helper(_fn)) is not None:
                register.filter(_fn_obj.__name__, _fn_obj)

    def parse(self, context: dict) -> str:
        """
        Function to parse the tmd file into a html string
        :param context: dictionary of context variables
        :return: html string
        """
        text = self._modify(self.raw, {
            r"\/\/.*?\n": r"\n",
            r"(-\[.+?\n)": r"-[\n\1",
        }) + "-["
        re_keys = re.compile(r"(?:^|\n)(?:-\[(.*?)]((?:.*?\r?\n?)*)-\[)+")
        # Todo: Fix for misaligned keys/tags
        key_list = re_keys.findall(text)
        keys = {i[0].strip(): i[1].strip() for i in key_list}
        if "extends" in keys and keys["extends"] not in ["default", ""]:
            self.final = f"{{% extends '{keys['extends'].replace('.', '/')}.html' %}}"
            keys.pop("extends")
        else:
            self.final = "{% extends 'base/_base.html' %}"
        if "filters" in keys:
            self.filters = keys["filters"].split("\n")
            keys.pop("filters")
        if "context" in keys:
            self.tmd_context = keys["context"]
            keys.pop("context")
            context = self._infer_helper(self.tmd_context + '\n', context)
        for _k, _v in keys.items():
            if _k != "body":
                self.final += f"{{% block {_k} %}} {_v} {{% endblock %}}"
        self._register(self.filters)
        self.body = re.sub(r"\\\s*?\n", "", keys["body"])
        for i in range(6, 0, -1):
            re_h = re.compile(rf"#{{{i}}}\s+(.*?)\n")
            self.body = re_h.sub(rf"<h{i}>\1</h{i}>", self.body)
        self.body = self._modify(self.body, {
            r"\*\*(.*?)\*\*": r"<b>\1</b>",
            r"\*(.*?)\*": r"<i>\1</i>",
            r"__(.+)?__": r"<u>\1</u>",
            r"-{3,}\s*?\n": r"<hr>",
        })
        self.final += f"{{% block body %}}{linebreaks(self.body)}{{% endblock %}}"
        return Template(self.final).render(Context(context))


def err(exc_, err_):
    # Todo: improve the error handling
    """
    Error handling
    """
    return Template("Something went wrong :( <br>"
                    "{{ error|linebreaks }}<br>"
                    "{{ err|linebreaks }}").render(Context({"error": exc_, "err": err_}))


def parse(text, context):
    """
    Function to parse the tmd file into a html string
    Wraps around Parse.parse()
    :param text: contends of the tmd file
    :param context: dictionary of context variables
    """
    try:
        return Parse(text).parse(context)
    except TemplateSyntaxError as exc:
        return err(exc, "")
    except AttributeError as exc:
        return err(exc, "This error can occur if filter or tag names begin with `_`")
    except TemplateDoesNotExist as exc:
        return err(exc, f"\nInvalid value for -[extends], {str(exc)} not found")
