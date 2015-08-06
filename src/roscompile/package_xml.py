from  xml.dom.minidom import parse
from resource_retriever import get
from roscompile.config import CFG
import operator, collections

IGNORE_PACKAGES = ['roslib']
IGNORE_LINES = [s + '\n' for s in get('package://roscompile/data/package.ignore').read().split('\n') if len(s)>0]

ORDERING = ['name', 'version', 'description', 
            ['maintainer', 'license', 'author', 'url'],
            'buildtool_depend', 'build_depend', 'run_depend', 'test_depend', 
            'export']

def get_ordering_index(name):
    for i, o in enumerate(ORDERING):
        if type(o)==list:
            if name in o:
                return i
        elif name==o:
            return i
    if name:        
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
    def __init__(self, fn):
        self.tree = parse(fn)
        self.root = self.tree.childNodes[0]
        self.header = '<?xml' in open(fn).read()
        self.fn = fn
        
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

    def get_packages(self, build=True):
        if build:
            key = 'build_depend'
        else:
            key = 'run_depend'

        pkgs = []
        for el in self.root.getElementsByTagName(key):
            pkgs.append( str(el.childNodes[0].nodeValue) )
        return pkgs
        
    def get_people(self, tag):
        people = {}
        for el in self.root.getElementsByTagName(tag):
            name = str(el.childNodes[0].nodeValue)
            email = el.getAttribute('email')
            people[name] = email
        return people

    def update_people(self, tag, people, replace={}):
        for el in self.root.getElementsByTagName(tag):
            name = str(el.childNodes[0].nodeValue)
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
                export.parentNode.removeChild(export)
                print '\tRemoving empty export tag'

    def insert_new_elements(self, name, values, i):
        x = []
        for pkg in values:
            if pkg in IGNORE_PACKAGES:
                continue
            print '\tInserting %s: %s'%(name, pkg)
            x.append(self.tree.createTextNode('\n' + ' '*self.std_tab))
            node = self.tree.createElement(name)
            node.appendChild(self.tree.createTextNode(pkg))
            x.append(node)

        self.root.childNodes = self.root.childNodes[:i-1] + x  + self.root.childNodes[i-1:]

    def add_packages(self, pkgs, build=True):
        for pkg in self.get_packages(build):
            if pkg in pkgs:
                pkgs.remove(pkg)

        state = 0
        i = 0
        while i < len(self.root.childNodes):
            child = self.root.childNodes[i]
            if child.nodeType==child.TEXT_NODE:
                i += 1
                continue

            name = str(child.nodeName)
            if name == 'build_depend':
                state = 1
            elif name == 'run_depend':
                if state <= 1 and build:
                    self.insert_new_elements('build_depend', pkgs, i)
                    i += len(pkgs)*2
                state = 2
            elif state == 2:
                if not build:
                    self.insert_new_elements('run_depend', pkgs, i)
                    i += len(pkgs)*2
                state = 3
            i += 1
        if state==0:
            if build:
                self.insert_new_elements('build_depend', pkgs, i)
            else:
                self.insert_new_elements('run_depend', pkgs, i)
        elif state == 2 and not build:
            self.insert_new_elements('run_depend', pkgs, i)

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
        
        alpha = CFG.should('alphabetize_depends')
        key = lambda d: get_sort_key(d[0], alpha)
        
        for a,b in sorted(chunks, key=key):
            self.root.childNodes += b


    def output(self, new_fn=None):
        if CFG.should('enforce_manifest_ordering'):
            self.enforce_ordering()
            
        if new_fn is None:
            new_fn = self.fn
        s = self.tree.toxml()
        if not self.header:
            s = s.replace('<?xml version="1.0" ?>', '').strip()
        else:
            s = s.replace(' ?><package>', '?>\n<package>')
            
        if CFG.should('remove_dumb_package_comments'):
            for line in IGNORE_LINES:
                s = s.replace(line, '')
                
        if CFG.should('remove_empty_package_lines'):        
            while '\n\n\n' in s:    
                s = s.replace('\n\n\n', '\n\n')
        
        old_s = open(new_fn, 'r').read()
        if old_s.strip() == s:
            return
            
        f = open(new_fn, 'w')
        f.write(s)
        f.write('\n')
        f.close()
