from  xml.dom.minidom import parse

IGNORE_PACKAGES = ['roslib']

class PackageXML:
    def __init__(self, fn):
        self.tree = parse(fn)
        self.root = self.tree.childNodes[0]
        self.header = '<?xml' in open(fn).read()
        self.fn = fn

    def get_packages(self, build=True):
        if build:
            key = 'build_depend'
        else:
            key = 'run_depend'

        pkgs = []
        for el in self.root.getElementsByTagName(key):
            pkgs.append( str(el.childNodes[0].nodeValue) )
        return pkgs

    def insert_new_elements(self, name, values, i):
        x = []
        for pkg in values:
            if pkg in IGNORE_PACKAGES:
                continue
            print '\tInserting %s: %s'%(name, pkg)
            x.append(self.tree.createTextNode('\n  '))
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

    def output(self, new_fn=None):
        if new_fn is None:
            new_fn = self.fn
        s = self.tree.toxml()
        if not self.header:
            s = s.replace('<?xml version="1.0" ?>', '').strip()
        else:
            s = s.replace(' ?><package>', '?>\n<package>')
        
        old_s = open(new_fn, 'r').read()
        if old_s.strip() == s:
            return       
            
        f = open(new_fn, 'w')
        f.write(s)
        f.write('\n')
        f.close()
