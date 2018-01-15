from xml.dom.minidom import parse
from collections import OrderedDict
import os.path

NS_PATTERN = '%s::%s'

class PluginXML:
    def __init__(self, fn):
        self.fn = fn
        self.CL = False
        self.libraries = OrderedDict()

        if os.path.exists(self.fn):
            self.read()

    def read(self):
        tree = parse(self.fn)

        self.CL = len(tree.getElementsByTagName('class_libraries')) > 0

        for el in tree.getElementsByTagName('library'):
            path = el.getAttribute('path')
            cls = OrderedDict()
            self.libraries[path] = cls

            for clstag in el.getElementsByTagName('class'):
                d = {}
                d['base_class_type'] = clstag.getAttribute('base_class_type')
                d['type'] = clstag.getAttribute('type')
                d['name'] = clstag.getAttribute('name')

                desc = ''
                for tag in clstag.getElementsByTagName('description'):
                    if len(tag.childNodes) == 0:
                        continue
                    desc += str(tag.childNodes[0].nodeValue)
                d['description'] = desc

                cls[d['type']] = d

    def insert_if_needed(self, pkg, name, base_pkg, base_name, description='', library=None):
        if library is None:
            if len(self.libraries) == 0:
                library = 'INSERT_NAME_OF_LIBRARY'
            else:
                library = self.libraries.keys()[0]
        else:
            if 'lib/lib' not in library:
                library = 'lib/lib' + library

        if library not in self.libraries:
            self.libraries[library] = OrderedDict()

        full_name = NS_PATTERN % (pkg, name)
        if full_name not in self.libraries[library]:
            self.libraries[library][full_name] = {'base_class_type': NS_PATTERN % (base_pkg, base_name),
                                                  'type': full_name,
                                                  'description': description}

    def write(self):
        with open(self.fn, 'w') as f:
            f.write(str(self))

    def __repr__(self):
        s = ''
        indent = 0
        CL = len(self.libraries) > 1 or self.CL
        if CL:
            s += '<class_libraries>\n'
            indent += 2

        for name, lib in self.libraries.iteritems():
            s += ' ' * indent + '<library path="%s">\n' % name
            for t, clib in lib.iteritems():
                s += self.class_str(clib, indent + 2)
            s += ' ' * indent + '</library>\n'

        if CL:
            s += '</class_libraries>\n'
        return s

    def class_str(self, lib, indent):
        s = ' ' * indent + '<class'
        for at in ['name', 'type', 'base_class_type']:
            if at in lib and len(lib[at]) > 0:
                s += ' %s="%s"' % (at, lib[at])
        s += '>\n' + (' ' * (indent + 2))
        s += '<description>%s</description>' % lib.get('description', '')

        s += '\n' + (' ' * indent) + '</class>\n'
        return s
