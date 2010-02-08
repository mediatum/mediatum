
import os
import sys
import core.config as config

from utils.utils import splitpath


contentstyles = {}

class ContentStyle:
    def __init__(self):
        self.type = "type"
        self.name = "name"
        self.label = "label"
        self.icon = "icon"
        self.template = "template"
        
    def getType(self):
        return self.type
    
    def getName(self):
        return self.name
    
    def getLabel(self):
        return self.label

    def getIcon(self):
        return self.icon

    def getTemplate(self):
        return self.template
        
        
def getContentStyles(type, name=""):
    global contentstyles

    if len(contentstyles)==0:
        styles = {}
        for root, dirs, files in os.walk(os.path.join(config.basedir, 'web/frontend/styles')):
            for name in [f for f in files if f.endswith(".py") and f!="__init__.py"]:
                m = __import__("web.frontend.styles." + name[:-3])
                m = eval("m.frontend.styles."+name[:-3]+"."+name[:-3]+"()")
                styles[name[:-3]] = m
             
        # test for external styles by plugin
        for k,v in config.getsubset("plugins").items():
            path, module = splitpath(v)
            try:
                sys.path += [path+".styles"]
                
                for root, dirs, files in os.walk(os.path.join(config.basedir, v+"/styles")):
                    for name in [f for f in files if f.endswith(".py") and f!="__init__.py"]:
                        m = __import__(module+".styles."+name[:-3])
                        m = eval("m.styles."+name[:-3])
                        styles[name[:-3]] = m
            except ImportError:
                pass # no styles in plugin
        contentstyles = styles
        
    if name!="":
        if name in contentstyles.keys():
            return contentstyles[name]
        else:
            return contentstyles.values()[0]

    return filter(lambda x: x.getType()==type, contentstyles.values())
