from  xml.dom.minidom import parse
from collections import OrderedDict
import os.path

class PluginXML:
    def __init__(self, fn):
        self.fn = fn
        self.CL = False
        self.libraries = OrderedDict()
        
        if os.path.exists(self.fn):
            self.read()
        
    def read(self):
        tree = parse(self.fn)

        self.CL = len(tree.getElementsByTagName('class_libraries'))>0

        for el in tree.getElementsByTagName('library'):
            path = el.getAttribute('path')
            cls = OrderedDict()
            self.libraries[ path ] = cls
            
            for clstag in el.getElementsByTagName('class'):
                d = {}
                d['base_class_type'] = clstag.getAttribute('base_class_type')
                d['type'] = clstag.getAttribute('type')
                d['name'] = clstag.getAttribute('name')
                
                desc = ''
                for tag in clstag.getElementsByTagName('description'):
                    desc += str(tag.childNodes[0].nodeValue)
                d['description'] = desc    
                
                cls[ d['type'] ] = d
    
    def __repr__(self):
        s = ''
        indent = 0
        CL = len(self.libraries)>1 or self.CL
        if CL:
            s += '<class_libraries>\n'
            indent += 2
            
        for name, lib in self.libraries.iteritems():
            s += ' '*indent + '<library path="%s">\n'%name
            for t, clib in lib.iteritems():
                s += self.class_str(clib, indent+2)
            s += ' '*indent + '</library>\n'
        
        if CL:
            s += '</class_libraries>\n'    
        return s
        
    def class_str(self, lib, indent):
        s = ' ' * indent + '<class'
        for at in ['name', 'type', 'base_class_type']:
            if at in lib and len(lib[at])>0:
                s += ' %s="%s"'%(at, lib[at])
        s += '>\n' + (' '*(indent+2))
        s += '<description>%s</description>'%lib.get('description', '')
        
        s += '\n' + (' '*indent) + '</class>\n'
        return s
