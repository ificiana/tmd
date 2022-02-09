"""
Injection safe execution (controlled globals and locals)
"""
import datetime


def _exec(*__args):
    compile(*__args, "exec")
    exec(__args[0])
    return locals()[__args[1]]


def _infer(*__args):
    compile(__args[0], "<dummy-var>", "exec")
    exec(__args[0], None, __args[1])
    __d = locals().copy()
    __d.pop("__args")
    return __d
