# Python
import os

# Zope
from zope.tales.engine import Engine as TALESEngine
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talgenerator import TALGenerator

# project
import ophelia.publisher, ophelia.template


###########
# functions

getScriptGlobals = ophelia.publisher.get_script_globals

def getContext():
    return getScriptGlobals()["context"]

def getTalesNames():
    return getScriptGlobals()["tales_names"]
