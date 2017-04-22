from  xml.dom.minidom import parse
from roscompile.config import CFG
import operator, collections, re
from roscompile.util import clean_contents, remove_blank_lines

IGNORE_PACKAGES = ['roslib']

DEPEND_ORDERING = ['buildtool_depend', 'depend', 'build_depend', 'build_export_depend',
'run_depend', 'exec_depend', 'test_depend', 'doc_depend']

ORDERING = ['name', 'version', 'description',
            ['maintainer', 'license', 'author', 'url']] + \
            DEPEND_ORDERING + \
            ['export']

INDENT_PATTERN = re.compile('\n *')

def get_ordering_index(name, whiny=True):
    for i, o in enumerate(ORDERING):
        if type(o)==list:
            if name in o:
                return i
        elif name==o:
            return i
    if name and whiny:
        print '\tUnsure of ordering for', name
    return len(ORDERING)

def get_sort_key(node, alphabetize_depends=True):
    if node:
        name = node.nodeName
    else:
        name = None

    index = get_ordering_index(name)

    if not alphabetize_depends:
        return index
    if name and 'depend' in name:
        return index, node.firstChild.data
    else:
        return index, None

def count_trailing_spaces(s):
    c = 0
    while c < len(s) and s[-c-1]==' ':
        c += 1
    return c

class PackageXML:
    def __init__(self, name, fn):
        self.name = name
        self.tree = parse(fn)
        self.root = self.tree.childNodes[0]
        self.header = '<?xml' in open(fn).read()
        self.fn = fn
        self._format = None

        tab_ct = collections.defaultdict(int)
        for c in self.root.childNodes:
            if c.nodeType == c.TEXT_NODE:
                spaces = count_trailing_spaces(c.data)
                tab_ct[spaces] += 1
        self.std_tab = max(tab_ct.iteritems(), key=operator.itemgetter(1))[0]

        if CFG.should('enforce_package_tabbing'):
            for c in self.root.childNodes:
                if c.nodeType == c.TEXT_NODE and c!=self.root.childNodes[-1]:
                    spaces = count_trailing_spaces(c.data)
                    if spaces > self.std_tab:
                        c.data = c.data[: self.std_tab-spaces]
                    elif spaces < self.std_tab:
                        c.data = c.data + ' '*(self.std_tab-spaces)

    @property
    def format(self):
        if self._format is not None:
            return self._format
        if not self.root.hasAttribute('format'):
            self._format = 1
        else:
            self._format = int(self.root.attributes['format'].value)
        return self._format

    def get_packages_by_tag(self, tag):
        pkgs = []
        for el in self.root.getElementsByTagName(tag):
            pkgs.append(el.childNodes[0].nodeValue)
        return pkgs

    def get_packages(self, build=True):
        keys = []
        if build:
            keys.append('build_depend')
        if self.format == 1 and not build:
            keys.append('run_depend')
        if self.format == 2:
            keys.append('depend')
            if not build:
                keys.append('exec_depend')
        pkgs = []
        for key in keys:
            pkgs += self.get_packages_by_tag(key)
        return pkgs

    def get_people(self, tag):
        people = {}
        for el in self.root.getElementsByTagName(tag):
            name = el.childNodes[0].nodeValue
            email = el.getAttribute('email')
            people[name] = email
        return people

    def update_people(self, tag, people, replace={}):
        for el in self.root.getElementsByTagName(tag):
            name = el.childNodes[0].nodeValue
            if name in replace:
                nn = replace[name]
                el.childNodes[0].nodeValue = nn
                el.setAttribute( 'email', people[nn] )
                print '\tReplacing %s with %s as %s'%(name, nn, tag)
            elif name in people:
                if len(people[name])>0:
                    if el.hasAttribute('email') and el.getAttribute('email')==people[name]:
                        continue
                    el.setAttribute( 'email', people[name] )
                    print '\tSetting %s\'s email to %s'%(name, people[name])

    def get_plugin_xmls(self):
        xmls = []
        export = self.root.getElementsByTagName('export')
        if len(export)<1:
            return xmls
        for ex in export:
            for n in ex.childNodes:
                if n.nodeType == self.root.ELEMENT_NODE:
                    plugin = n.getAttribute('plugin').replace('${prefix}/', '')
                    xmls.append(( n.nodeName, plugin))
        return xmls

    def add_plugin_export(self, fn, tipo):
        exports = self.root.getElementsByTagName('export')
        if len(exports)==0:
            ex = self.tree.createElement('export')
            self.root.appendChild(ex)
        else:
            ex = exports[0]
        pe = self.tree.createElement(tipo)
        pe.setAttribute('plugin', '${prefix}/' + fn )
        ex.appendChild(pe)

    def remove_element(self, element):
        parent = element.parentNode
        index = parent.childNodes.index(element)
        if index > 0:
            previous = parent.childNodes[index-1]
            if previous.nodeType == previous.TEXT_NODE and INDENT_PATTERN.match(previous.nodeValue):
                parent.removeChild(previous)
        parent.removeChild(element)

    def remove_empty_export(self):
        exports = self.root.getElementsByTagName('export')
        if len(exports)==0:
            return
        for export in exports:
            remove = True

            for c in export.childNodes:
                if c.nodeType == c.ELEMENT_NODE:
                    remove = False

            if remove:
                self.remove_element(export)
                print '\tRemoving empty export tag'

    def is_metapackage(self):
        for node in self.root.getElementsByTagName('export'):
            for child in node.childNodes:
                if child.nodeType == child.ELEMENT_NODE:
                    if child.nodeName == 'metapackage':
                        return True
        return False

    def remove_dependencies(self, name, pkgs, quiet=False):
        for el in self.root.getElementsByTagName(name):
            pkg = el.childNodes[0].nodeValue
            if pkg in pkgs:
                if not quiet:
                    print '\tRemoving %s %s'%(name, pkg)
                self.remove_element(el)

    def get_child_indexes(self):
        tags = collections.defaultdict(list)
        i = 0
        current = None
        current_start = 0
        current_last = 0
        while i < len(self.root.childNodes):
            child = self.root.childNodes[i]
            if child.nodeType==child.TEXT_NODE:
                i += 1
                continue

            name = child.nodeName
            if name != current:
                if current:
                    tags[current].append((current_start, current_last))
                current_start = i
                current = name
            current_last = i
            i += 1
        if current:
            tags[current].append((current_start, current_last))
        return dict(tags)

    def insert_new_elements(self, name, values):
        x = []
        indexes = self.get_child_indexes()
        for pkg in values:
            if pkg in IGNORE_PACKAGES:
                continue
            print '\tInserting %s: %s'%(name, pkg)
            x.append(self.tree.createTextNode('\n' + ' '*self.std_tab))
            node = self.tree.createElement(name)
            node.appendChild(self.tree.createTextNode(pkg))
            x.append(node)

        index = None
        if name in indexes:
            index = indexes[name][-1][-1]
        else:
            previous = None
            max_index = get_ordering_index(name, whiny=False)
            best_tag = None
            best_index = None
            for tag in indexes:
                ni = get_ordering_index(tag, whiny=False)
                if ni < max_index and (best_tag is None or ni > best_index):
                    best_tag = tag
                    best_index = ni
            if best_tag is None:
                index = len(self.root.childNodes)
            else:
                index = indexes[best_tag][-1][-1]
        self.root.childNodes = self.root.childNodes[:index+1] + x  + self.root.childNodes[index+1:]

    def add_packages(self, pkgs, build=True):
        for pkg in self.get_packages(build):
            if pkg in pkgs:
                pkgs.remove(pkg)
        if len(pkgs)==0:
            return

        indexes = self.get_child_indexes()
        if build:
            new_tag = 'build_depend'
        elif self.format == 1:
            new_tag = 'run_depend'
        else:
            new_tag = 'exec_depend'
        self.insert_new_elements(new_tag, pkgs)

    def replace_package_set(self, source_tags, new_tag):
        intersection = None
        for tag in source_tags:
            pkgs = set(self.get_packages_by_tag(tag))
            if intersection is None:
                intersection = pkgs
            else:
                intersection = intersection.intersection(pkgs)
        for tag in source_tags:
            self.remove_dependencies(tag, intersection)
        self.insert_new_elements(new_tag, intersection)

    def convert_to_format_2(self):
        self.format = 2
        self.root.setAttribute('format', '2')
        self.replace_package_set(['build_depend', 'run_depend'], 'depend')
        self.replace_package_set(['run_depend'], 'exec_depend')

    def enforce_ordering(self):
        chunks = []
        current = []
        group = None
        for x in self.root.childNodes:
            current.append(x)
            if x.nodeType==x.ELEMENT_NODE:
                chunks.append( (x, current) )
                current = []
        if len(current)>0:
            chunks.append( (None, current) )

        self.root.childNodes = []

        alpha = CFG.should('alphabetize')
        key = lambda d: get_sort_key(d[0], alpha)

        for a,b in sorted(chunks, key=key):
            self.root.childNodes += b


    def output(self, new_fn=None):
        if CFG.should('enforce_manifest_ordering'):
            self.enforce_ordering()
        if self.format==2 and CFG.should('consolidate_depend_in_package_xml'):
            self.replace_package_set(['build_depend', 'build_export_depend', 'exec_depend'], 'depend')

        if new_fn is None:
            new_fn = self.fn
        s = self.tree.toxml(self.tree.encoding)
        if not self.header:
            s = s.replace('<?xml version="1.0" ?>', '').strip()
        else:
            s = s.replace('?><package', '?>\n<package')
            s = s.replace(' ?>', '?>')

        if CFG.should('remove_dumb_package_comments'):
            s = clean_contents(s, 'package', {'package': self.name})

        if CFG.should('remove_empty_package_lines'):
            s = remove_blank_lines(s)

        old_s = open(new_fn, 'r').read().decode('UTF-8')
        if old_s.strip() == s:
            return

        f = open(new_fn, 'w')
        f.write(s.encode('UTF-8'))
        f.write('\n')
        f.close()
