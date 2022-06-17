import re
from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError


class Launch:
    def __init__(self, rel_fn, file_path):
        self.rel_fn = rel_fn
        self.file_path = file_path

    def get_dependencies(self):
        d = set()
        d.update(self.get_node_pkgs())
        d.update(self.get_include_pkgs())
        d.update(self.get_misc_pkgs())
        return sorted(d)

    def __repr__(self):
        return self.rel_fn


class LaunchXML(Launch):
    def __init__(self, rel_fn, file_path):
        Launch.__init__(self, rel_fn, file_path)
        try:
            self.tree = parse(self.file_path)
            self.test = len(self.tree.getElementsByTagName('test')) > 0
        except ExpatError:  # this is an invalid xml file
            self.test = False

    def get_node_pkgs(self):
        s = set()
        for node in self.tree.getElementsByTagName('node'):
            s.add(str(node.getAttribute('pkg')))
        return sorted(s)

    def get_include_pkgs(self):
        s = set()
        for node in self.tree.getElementsByTagName('include'):
            el = node.getAttribute('file')
            if 'find' in el:
                i = el.index('find')
                i2 = el.index(')', i)
                s.add(el[i + 5:i2])
        return sorted(s)

    def get_misc_pkgs(self):
        s = set()
        xml_str = self.tree.toxml()
        for x in re.finditer(r'\$\(find ([^\)]*)\)', xml_str):
            s.add(x.group(1))
        # rosrun PKG (e.g. <param command="rosrun xacro xacro.py xacrofile.xacro" />
        for x in re.finditer(r'rosrun\s+(\w+)\s', xml_str):
            s.add(x.group(1))
        return s
