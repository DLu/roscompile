from  xml.dom.minidom import parse
import re

class Launch:
    def __init__(self, fn):
        self.tree = parse(fn)

    def get_node_pkgs(self):
        s = set()
        for node in self.tree.getElementsByTagName('node'):
            s.add( str(node.getAttribute('pkg')) )
        return sorted(list(s))

    def get_include_pkgs(self):
        s = set()
        for node in self.tree.getElementsByTagName('include'):
            el = node.getAttribute('file') 
            if 'find' in el:
                i = el.index('find')
                i2 = el.index(')', i)
                s.add( el[i+5:i2] )
        return sorted(list(s))
        
    def get_misc_pkgs(self):
        s = set()
        for x in re.finditer('\$\(find (.*)\)', self.tree.toxml()):
            s.add(x.group(1))
        return s

    def get_dependencies(self):
        d = set()
        d.update(self.get_node_pkgs())
        d.update(self.get_include_pkgs())
        d.update(self.get_misc_pkgs())
        return sorted(list(d))

