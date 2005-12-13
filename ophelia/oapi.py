# Python
import inspect

# project
from ophelia import publisher


########################
# exceptions and classes

StopTraversal = publisher.StopTraversal

Namespace = publisher.Namespace


###########
# functions

def getScriptGlobals():
    for frame_record in inspect.stack():
        candidate = frame_record[0].f_globals
        if type(candidate) == publisher._ScriptGlobals:
            return candidate
    else:
        raise LookupError("Could not find script globals.")


def getContext():
    return getScriptGlobals()["context"]

def getMacros():
    return getScriptGlobals()["macros"]

def getRequest():
    return getScriptGlobals()["request"]

def getTraversal():
    return getScriptGlobals()["traversal"]
