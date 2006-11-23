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

def getLogError():
    return getScriptGlobals()["log_error"]

def getContext():
    return getScriptGlobals()["context"]

def getMacros():
    return getScriptGlobals()["macros"]

def getRequest():
    return getScriptGlobals()["request"]

def getTalesNames():
    return getScriptGlobals()["tales_names"]


def loadMacros(*args):
    publisher = ophelia.publisher.get_publisher()
    macros = getMacros()
    log_error = getLogError()
    for name in args:
        file_path = os.path.join(os.path.dirname(publisher.file_path), name)
        try:
            content = file(file_path).read()
        except:
            log_error("Can't read macro file at " + file_path)
            raise

        script, template_ = publisher.splitter(content)
        if script:
            log_error("Macro file contains a script at " + file_path)
            raise ValueError("Macro file contains a script at " + file_path)

        generator = TALGenerator(TALESEngine, xml=False,
                                 source_file=file_path)
        parser = HTMLTALParser(generator)

        try:
            parser.parseString(template_)
        except:
            log_error("Can't compile template at " + file_path)
            raise

        program, macros_ = parser.getCode()
        macros.update(macros_)
