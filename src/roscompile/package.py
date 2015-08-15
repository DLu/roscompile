import os
import os.path
import collections
import sys
from roscompile.launch import Launch
from roscompile.source import Source
from roscompile.setup_py import SetupPy
from roscompile.package_xml import PackageXML
from roscompile.plugin_xml import PluginXML
from roscompile.cmake import CMake
from roscompile.config import CFG

SRC_EXTS = ['.py', '.cpp', '.h']
CONFIG_EXTS = ['.yaml', '.rviz']
DATA_EXTS = ['.dae', '.jpg', '.stl', '.png']
MODEL_EXTS = ['.urdf', '.xacro', '.srdf']

EXTS = {'source': SRC_EXTS, 'config': CONFIG_EXTS, 'data': DATA_EXTS, 'model': MODEL_EXTS}
BASIC = ['package.xml', 'CMakeLists.txt']
SIMPLE = ['.launch', '.msg', '.srv', '.action']
PLUGIN_CONFIG = 'plugins'
EXTRA = 'Extra!'

def query(s):
    return raw_input(s).decode(sys.stdin.encoding)

def match(ext):
    for name, exts in EXTS.iteritems():
        if ext in exts:
            return name
    return None

class Package:
    def __init__(self, root):
        self.root = root
        self.name = os.path.split(os.path.abspath(root))[-1]
        self.manifest = PackageXML(self.root + '/package.xml')
        self.cmake = CMake(self.root + '/CMakeLists.txt', self.name)
        self.files = self.sort_files()
        self.sources = [Source(source) for source in self.files['source']]

    def sort_files(self, print_extras=False):
        data = collections.defaultdict(list)
        
        plugins = self.manifest.get_plugin_xmls()
        
        for root,dirs,files in os.walk(self.root):
            if '.git' in root or '.svn' in root:
                continue
            for fn in files:
                ext = os.path.splitext(fn)[-1]
                full = '%s/%s'%(root, fn)
                if fn[-1]=='~':
                    continue
                ext_match = match(ext)

                if ext_match:
                    data[ext_match].append(full)
                elif ext in SIMPLE:
                    name = ext[1:]
                    data[name].append(full)
                elif ext == '.cfg' and 'cfg/' in fn:
                    data['cfg'].append(full)
                elif fn in BASIC:
                    data[None].append(full)
                else:
                    found = False
                    for tipo, pfilename in plugins:
                        if fn==pfilename:
                            data[PLUGIN_CONFIG].append( (full, tipo) )
                            found = True
                            break
                    if found:
                        continue   

                    data[EXTRA].append(full)
        if print_extras and len(data[EXTRA])>0:
            for fn in data[EXTRA]:
                print '    ', fn

        return data

    def get_build_dependencies(self):
        packages = set()
        if CFG.should('read_source'):
            for source in self.sources:
                packages.update(source.get_dependencies())
            if self.name in packages:
                packages.remove(self.name)            
        return sorted(list(packages))

    def get_run_dependencies(self):
        packages = set()
        if CFG.should('read_launches'):
            for launch in self.files['launch']:
                x = Launch(launch)
                packages.update(x.get_dependencies())
            if self.name in packages:
                packages.remove(self.name)
        return sorted(list(packages))

    def get_dependencies(self, build=True):
        if build:
            return self.get_build_dependencies()
        else:
            return self.get_run_dependencies()

    def update_manifest(self):
        for build in [True, False]:
            dependencies = self.get_dependencies(build)
            if build:
                self.manifest.add_packages(dependencies, build)
            self.manifest.add_packages(dependencies, False)
            
        if len(self.files['msg']) + len(self.files['srv']) + len(self.files['action']) > 0:
            self.manifest.add_packages(['message_runtime'], True)
            
        if CFG.should('remove_empty_export_tag'):
            self.manifest.remove_empty_export()

        self.manifest.output()

    def print_files(self):
        for name, files in sorted(self.files.items()):
            if len(files)==0:
                continue
            print name
            for fn in sorted(files):
                print '\t',fn
        
    def update_cmake(self):
        self.cmake.check_dependencies( self.get_dependencies() )        

        self.cmake.check_generators( self.files['msg'], self.files['srv'], self.files['action'], self.files['cfg'])
        
        setup = self.get_setup_py()
        if setup and setup.valid and \
            'catkin_python_setup' not in self.cmake.content_map:
            self.cmake.add_command('catkin_python_setup()')
            
        self.cmake.output()

    def get_python_source(self):
        sources = []        
        for source in self.sources:
            if source.python and 'setup.py' not in source.fn:
                sources.append(source)
        return sources     
        
    def get_setup_py(self):
        sources = self.get_python_source()
        if len(sources)==0:
            return
            
        setup = SetupPy(self.name, self.root, sources)
        return setup           
        
    def generate_setup(self):
        setup = self.get_setup_py()
        if not setup:
            return
        setup.write_if_needed()
        return
        
    def check_plugins(self):
        plugins = []
        for source in self.sources:
            plugins += source.get_plugins()
            
        configs = {}
        for filename, tipo in self.files[PLUGIN_CONFIG]:
            configs[tipo] = PluginXML(filename)
            
        pattern = '%s::%s'    
        for pkg1, name1, pkg2, name2 in plugins:
            if pkg2 not in configs:
                configs[pkg2] = PluginXML( self.root + '/plugins.xml')
                self.manifest.add_plugin_export('plugins.xml', pkg2)
            configs[pkg2].insert_if_needed(pattern%(pkg1, name1), pattern%(pkg2, name2))

        for config in configs.values():
            config.write()
        self.manifest.output()    
        
    def get_people(self):
        people = {}
        people['maintainers'] = self.manifest.get_people('maintainer')
        people['authors'] = self.manifest.get_people('author')
        return people

    def update_people(self, people, replace={}):
        self.manifest.update_people('maintainer', people, replace)
        self.manifest.update_people('author', people, replace)

def get_packages(root_fn='.'):
    packages = []
    for root,dirs,files in os.walk(root_fn):
        if '.git' in root:
            continue
        if 'package.xml' in files:
            packages.append(Package(root))
    return packages

def get_people_info(pkgs):
    people = {}
    replace = {}
    
    for package in pkgs:
        for k,v in package.get_people().iteritems():
            people.update(v)
            
    if 'canonical_names' not in CFG:
        name = query('What is your name (exactly as you\'d like to see it in the documentation)? ')
        email = query('What is your email (for documentation purposes)? ')

        CFG['canonical_names'] = [{'name': name, 'email': email}]
        
    for d in CFG['canonical_names']:
        people[ d['name'] ] = d['email']     
        
    while len(people)>1:
        print
        values = sorted(people.keys(), key=lambda d: d.lower())
        for i, n in enumerate(values):
            print '%d) %s %s'%(i, n, '(%s)'%people[n] if n in people else '')
        print
        c = query('Which name would you like to replace? (Enter #, or q to quit)')
        if c=='q':
            break
        try:
            c = int(c)
        except:
            continue
        if c < 0 or c > len(values):
            continue
        c2 = query('What do you want to replace it with? ')
        if c2=='q':
            break
        try:
            c2 = int(c2)            
        except:
            continue
        if c2 < 0 or c2>len(values) or c==c2:
            continue
        replace[ values[c] ] = values[c2]
        del people[ values[c] ] 
    return people, replace    
