from xml.dom.minidom import parse
import collections
import operator
import re

DEPEND_ORDERING = ['buildtool_depend', 'depend', 'build_depend', 'build_export_depend',
                   'run_depend', 'exec_depend', 'test_depend', 'doc_depend']

ORDERING = ['name', 'version', 'description',
            ['maintainer', 'license', 'author', 'url']] + DEPEND_ORDERING + ['export']

INDENT_PATTERN = re.compile('\n *')

PEOPLE_TAGS = ['maintainer', 'author']


def get_ordering_index(name, whiny=True):
    for i, o in enumerate(ORDERING):
        if type(o) == list:
            if name in o:
                return i
        elif name == o:
            return i
    if name and whiny:
        print '\tUnsure of ordering for', name
    return len(ORDERING)


def get_package_tag_index(s, key='<package'):
    if key not in s:
        return 0
    return s.index(key)


def count_trailing_spaces(s):
    c = 0
    while c < len(s) and s[-c - 1] == ' ':
        c += 1
    return c


class PackageXML:
    def __init__(self, fn):
        self.fn = fn
        self.tree = parse(fn)
        self.root = self.tree.getElementsByTagName('package')[0]
        contents = open(fn).read()
        self.header = contents[:get_package_tag_index(contents)]
        self._name = None
        self._format = None
        self._std_tab = None

    @property
    def name(self):
        if self._name is not None:
            return self._name
        name_tags = self.root.getElementsByTagName('name')
        if not name_tags:
            return
        name_tag = name_tags[0]
        self._name = name_tag.childNodes[0].nodeValue
        return self._name

    @property
    def format(self):
        if self._format is not None:
            return self._format
        if not self.root.hasAttribute('format'):
            self._format = 1
        else:
            self._format = int(self.root.attributes['format'].value)
        return self._format

    @property
    def std_tab(self):
        if self._std_tab is not None:
            return self._std_tab
        tab_ct = collections.defaultdict(int)
        for c in self.root.childNodes:
            if c.nodeType == c.TEXT_NODE:
                spaces = count_trailing_spaces(c.data)
                tab_ct[spaces] += 1
        if len(tab_ct) == 0:
            self._std_tab = 4
        else:
            self._std_tab = max(tab_ct.iteritems(), key=operator.itemgetter(1))[0]
        return self._std_tab

    def get_packages_by_tag(self, tag):
        pkgs = []
        for el in self.root.getElementsByTagName(tag):
            pkgs.append(el.childNodes[0].nodeValue)
        return pkgs

    def get_packages(self, mode='build'):
        keys = []
        if mode == 'build':
            keys.append('build_depend')
        if self.format == 1 and mode == 'run':
            keys.append('run_depend')
        if self.format == 2 and mode != 'test':
            keys.append('depend')
            if mode == 'run':
                keys.append('exec_depend')
        if mode == 'test':
            keys.append('test_depend')
        pkgs = []
        for key in keys:
            pkgs += self.get_packages_by_tag(key)
        return set(pkgs)

    def get_tab_element(self, tabs=1):
        return self.tree.createTextNode('\n' + ' ' * (self.std_tab * tabs))

    def get_child_indexes(self):
        """
           Return a dictionary where the keys are the types of nodes in the xml (build_depend, maintainer, etc)
           and the values are arrays marking the range of elements in the xml root that match that tag.

           For example, tags[build_depend] = [(5, 9), (11, 50)] means that elements [5, 9) and [11, 50) are
           either build_depend elements (or the strings between them)
        """
        tags = collections.defaultdict(list)
        i = 0
        current = None
        current_start = 0
        current_last = 0
        while i < len(self.root.childNodes):
            child = self.root.childNodes[i]
            if child.nodeType == child.TEXT_NODE:
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

    def get_insertion_index(self, tag):
        """ Returns the index where to insert a new element with the given tag type.
            If there are already elements of that type, then insert after the last matching element.
            Otherwise, look at the existing elements, and find ones that are supposed to come the closest
            before the given tag, and insert after them. If none found, add at the end.
        """
        indexes = self.get_child_indexes()
        if tag in indexes:
            return indexes[tag][-1][1]  # last match, end index

        max_index = get_ordering_index(tag, whiny=False)
        best_tag = None
        best_index = None
        for tag in indexes:
            ni = get_ordering_index(tag, whiny=False)
            if ni >= max_index:
                # This tag should appear after our tag
                continue

            if best_tag is None or ni > best_index or indexes[tag][-1] > indexes[best_tag][-1]:
                best_tag = tag
                best_index = ni

        if best_tag is None:
            return len(self.root.childNodes)
        else:
            return indexes[best_tag][-1][1]

    def insert_new_tags(self, tags):
        # Assumes all the tags have the same type
        if len(tags) == 0:
            return

        index = self.get_insertion_index(tags[0].tagName)
        tags_plus_indents = []
        for tag in tags:
            tags_plus_indents.append(self.get_tab_element())
            tags_plus_indents.append(tag)
        self.root.childNodes = self.root.childNodes[:index + 1] + tags_plus_indents + self.root.childNodes[index + 1:]

    def insert_new_packages(self, tag, values):
        elements_to_insert = []
        for pkg in sorted(values):
            print '\tInserting %s: %s' % (tag, pkg)
            node = self.tree.createElement(tag)
            node.appendChild(self.tree.createTextNode(pkg))
            elements_to_insert.append(node)
        self.insert_new_tags(elements_to_insert)

    def add_packages(self, build_depends, run_depends, test_depends=None, prefer_depend_tag=True):
        if self.format == 1:
            run_depends.update(build_depends)
        existing_build = self.get_packages('build')
        existing_run = self.get_packages('run')
        build_depends = build_depends - existing_build
        run_depends = run_depends - existing_run
        if self.format == 1:
            self.insert_new_packages('build_depend', build_depends)
            self.insert_new_packages('run_depend', run_depends)
        elif prefer_depend_tag:
            self.insert_new_packages('depend', build_depends.union(run_depends))
        else:
            both = build_depends.intersection(run_depends)
            self.insert_new_packages('depend', both)
            self.insert_new_packages('build_depend', build_depends - both)
            self.insert_new_packages('exec_depend', build_depends - both - existing_run)
            self.insert_new_packages('exec_depend', run_depends - both)

        if test_depends is not None and len(test_depends) > 0:
            existing_test = self.get_packages('test')
            test_depends = set(test_depends) - existing_build - build_depends - existing_test
            self.insert_new_packages('test_depend', test_depends)

    def remove_element(self, element):
        """ Remove the given element AND the text element before it if it is just an indentation """
        parent = element.parentNode
        index = parent.childNodes.index(element)
        if index > 0:
            previous = parent.childNodes[index - 1]
            if previous.nodeType == previous.TEXT_NODE and INDENT_PATTERN.match(previous.nodeValue):
                parent.removeChild(previous)
        parent.removeChild(element)

    def remove_dependencies(self, name, pkgs, quiet=False):
        for el in self.root.getElementsByTagName(name):
            pkg = el.childNodes[0].nodeValue
            if pkg in pkgs:
                if not quiet:
                    print '\tRemoving %s %s' % (name, pkg)
                self.remove_element(el)

    def get_elements_by_tags(self, tags):
        elements = []
        for tag in tags:
            elements += self.root.getElementsByTagName(tag)
        return elements

    def get_people(self):
        people = []
        for el in self.get_elements_by_tags(PEOPLE_TAGS):
            name = el.childNodes[0].nodeValue
            email = el.getAttribute('email')
            people.append((name, email))
        return people

    def update_people(self, target_name, target_email=None, search_name=None, search_email=None):
        for el in self.get_elements_by_tags(PEOPLE_TAGS):
            name = el.childNodes[0].nodeValue
            email = el.getAttribute('email') if el.hasAttribute('email') else ''
            if (search_name is None or name == search_name) and (search_email is None or email == search_email):
                el.childNodes[0].nodeValue = target_name
                if target_email:
                    el.setAttribute('email', target_email)
                print '\tReplacing %s %s/%s with %s/%s' % (el.nodeName, name, email, target_name, target_email)

    def get_license_element(self):
        els = self.root.getElementsByTagName('license')
        if len(els) == 0:
            return None
        return els[0]

    def get_license(self):
        el = self.get_license_element()
        return el.childNodes[0].nodeValue

    def set_license(self, license):
        el = self.get_license_element()
        el.childNodes[0].nodeValue = license

    def is_metapackage(self):
        for node in self.root.getElementsByTagName('export'):
            for child in node.childNodes:
                if child.nodeType == child.ELEMENT_NODE:
                    if child.nodeName == 'metapackage':
                        return True
        return False

    def get_plugin_xmls(self):
        """ Returns a mapping from the package name to a list of the relative path(s) for the plugin xml(s) """
        xmls = collections.defaultdict(list)
        export = self.root.getElementsByTagName('export')
        if len(export) == 0:
            return xmls
        for ex in export:
            for n in ex.childNodes:
                if n.nodeType == self.root.ELEMENT_NODE:
                    plugin = n.getAttribute('plugin').replace('${prefix}/', '')
                    xmls[n.nodeName].append(plugin)
        return xmls

    def add_plugin_export(self, pkg_name, xml_path):
        """ Adds the plugin configuration if not found. Adds export tag as needed.
            Returns the export tag it was added to."""
        export_tags = self.root.getElementsByTagName('export')
        if len(export_tags) == 0:
            export_tag = self.tree.createElement('export')
            self.insert_new_tags([export_tag])
            export_tags = [export_tag]

        attr = '${prefix}/' + xml_path
        for ex_tag in export_tags:
            for tag in ex_tag.childNodes:
                if tag.nodeName != pkg_name:
                    continue
                plugin = tag.attributes.get('plugin')
                if plugin and plugin.value == attr:
                    return

        ex_el = export_tags[0]
        pe = self.tree.createElement(pkg_name)
        pe.setAttribute('plugin', attr)
        ex_el.appendChild(pe)
        return ex_el

    def write(self, new_fn=None):
        if new_fn is None:
            new_fn = self.fn

        s = self.tree.toxml(self.tree.encoding)
        index = get_package_tag_index(s)
        s = self.header + s[index:]

        old_s = open(new_fn, 'r').read().decode('UTF-8')
        if old_s.strip() == s:
            return

        with open(new_fn, 'w') as f:
            f.write(s.encode('UTF-8'))
            f.write('\n')
