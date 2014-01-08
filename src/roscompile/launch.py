from  xml.dom.minidom import parse

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

    def get_dependencies(self):
        d = set()
        d.update(self.get_node_pkgs())
        d.update(self.get_include_pkgs())
        return sorted(list(d))

