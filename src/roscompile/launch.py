from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError
import re

class Launch:
    def __init__(self, fn):
        self.fn = fn
        try:
            self.tree = parse(fn)
            self.test = len(self.tree.getElementsByTagName('test')) > 0
            self.valid = len(self.tree.getElementsByTagName('launch')) > 0
        except ExpatError:  # this is an invalid xml file
            self.test = False
            self.valid = False

    def get_node_pkgs(self):
        s = set()
        for node in self.tree.getElementsByTagName('node'):
            s.add(str(node.getAttribute('pkg')))
        return sorted(list(s))

    def get_include_pkgs(self):
        s = set()
        for node in self.tree.getElementsByTagName('include'):
            el = node.getAttribute('file')
            if 'find' in el:
                i = el.index('find')
                i2 = el.index(')', i)
                s.add(el[i + 5:i2])
        return sorted(list(s))

    def get_misc_pkgs(self):
        s = set()
        xml_str = self.tree.toxml()
        for x in re.finditer('\$\(find ([^\)]*)\)', xml_str):
            s.add(x.group(1))
        # rosrun PKG (e.g. <param command="rosrun xacro xacro.py xacrofile.xacro" />
        for x in re.finditer('rosrun\s+(\w+)\s', xml_str):
            s.add(x.group(1))
        return s

    def get_dependencies(self):
        d = set()
        d.update(self.get_node_pkgs())
        d.update(self.get_include_pkgs())
        d.update(self.get_misc_pkgs())
        return sorted(list(d))
