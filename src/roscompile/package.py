import os
import os.path
import collections
import re
from roscompile.launch import Launch
from roscompile.source import Source
from roscompile.setup_py import SetupPy
from roscompile.package_xml import PackageXML
from roscompile.plugin_xml import PluginXML
from roscompile.cmake import CMake
from roscompile.config import CFG

SRC_EXTS = ['.py', '.cpp', '.h', '.hpp']
CONFIG_EXTS = ['.yaml', '.rviz']
DATA_EXTS = ['.dae', '.jpg', '.stl', '.png']
MODEL_EXTS = ['.urdf', '.xacro', '.srdf']

EXTS = {'source': SRC_EXTS, 'config': CONFIG_EXTS, 'data': DATA_EXTS, 'model': MODEL_EXTS}
BASIC = ['package.xml', 'CMakeLists.txt']
SIMPLE = ['.launch', '.msg', '.srv', '.action']
PLUGIN_CONFIG = 'plugins'
EXTRA = 'Extra!'

MAINPAGE_S = "/\*\*\s+\\\\mainpage\s+\\\\htmlinclude manifest.html\s+\\\\b %s\s+<!--\s+" + \
             "Provide an overview of your package.\s+-->\s+-->\s+[^\*]*\*/"

def match(ext):
    for name, exts in EXTS.iteritems():
        if ext in exts:
            return name
    return None

class Package:
    def __init__(self, root):
        self.root = root
        self.name = os.path.split(os.path.abspath(root))[-1]
        self.manifest = PackageXML(self.name, self.root + '/package.xml')
        self.cmake = CMake(self.root + '/CMakeLists.txt', self.name)
        self.plugins = {}
        self.files = self.sort_files()
        self.sources = [Source(source, self.root) for source in self.files['source']]
        self.setup_source_tags()

    def sort_files(self, print_extras=False):
        data = collections.defaultdict(list)

        plugins = self.manifest.get_plugin_xmls()

        for root, dirs, files in os.walk(self.root):
            if '.git' in root or '.svn' in root:
                continue
            for fn in files:
                ext = os.path.splitext(fn)[-1]
                full = '%s/%s' % (root, fn)
                if fn[-1] == '~' or fn[-4:] == '.pyc':
                    continue
                ext_match = match(ext)

                if ext_match:
                    data[ext_match].append(full)
                elif ext in SIMPLE:
                    name = ext[1:]
                    data[name].append(full)
                elif ext == '.cfg' and 'cfg/' in full:
                    data['cfg'].append(full)
                elif fn in BASIC:
                    data[None].append(full)
                else:
                    found = False
                    for tipo, pfilename in plugins:
                        if fn == pfilename:
                            data[PLUGIN_CONFIG].append(full)
                            self.plugins[tipo] = PluginXML(full)
                            found = True
                            break
                    if found:
                        continue

                    with open(full) as f:
                        l = f.readline()
                        if '#!' in l and 'python' in l:
                            data['source'].append(full)
                            continue

                    data[EXTRA].append(full)
        if print_extras and len(data[EXTRA]) > 0:
            for fn in data[EXTRA]:
                print '    ', fn

        return data

    def setup_source_tags(self):
        src_map = {}
        for source in self.sources:
            src_map[source.rel_fn] = source

        for tag, files in [('library', self.cmake.get_library_source()),
                           ('executable', self.cmake.get_executable_source()),
                           ('test', self.cmake.get_test_source())]:
            for fn in files:
                if fn in src_map:
                    src_map[fn].tags.add(tag)
                else:
                    print '    File %s found in CMake not found!'

    def get_build_dependencies(self):
        packages = set()
        for source in self.sources:
            packages.update(source.get_dependencies())
        if self.name in packages:
            packages.remove(self.name)
        return sorted(list(packages))

    def get_run_dependencies(self):
        packages = set()
        for launch in self.files['launch']:
            x = Launch(launch)
            packages.update(x.get_dependencies())
        if self.name in packages:
            packages.remove(self.name)
        return sorted(list(packages))

    def get_message_dependencies(self, exclude_python=True):
        d = set()
        for src in self.sources:
            if exclude_python and src.python:
                continue
            d.update(src.get_message_dependencies())
        return sorted(list(d))

    def get_dependencies_from_msgs(self):
        deps = set()
        for fn in self.files['msg'] + self.files['srv'] + self.files['action']:
            with open(fn) as f:
                for line in f:
                    if '#' in line:
                        line = line[:line.index('#')]
                    line = line.strip()
                    if line == '---' or line == '':
                        continue
                    if '=' in line.split():
                        line = line[:line.index('=')]
                    tipo, name = line.split()
                    if '/' not in tipo:
                        continue
                    package, part = tipo.split('/')
                    if package != self.name:
                        deps.add(package)
        if len(self.files['action']):
            deps.add('actionlib_msgs')
        return sorted(list(deps))

    def update_manifest(self):
        build_depends = self.get_build_dependencies()
        run_depends = self.get_run_dependencies()
        self.manifest.add_packages(build_depends, run_depends)

        if len(self.files['msg']) + len(self.files['srv']) + len(self.files['action']) > 0:
            md = self.get_dependencies_from_msgs()
            self.manifest.add_packages(['message_generation'] + md, ['message_runtime'] + md)

        if CFG.should('remove_empty_export_tag'):
            self.manifest.remove_empty_export()

        if self.manifest.is_metapackage() and CFG.should('update_metapackage_deps'):
            parent_path = os.path.abspath(os.path.join(self.root, '..'))
            parent_folder = os.path.split(parent_path)[1]
            if self.name == parent_folder:
                for package in get_packages(parent_path, create_objects=False):
                    pkg_name = os.path.split(package)[1]
                    self.manifest.add_packages([], [pkg_name])

        self.manifest.output()

    def print_files(self):
        for name, files in sorted(self.files.items()):
            if len(files) == 0:
                continue
            print name
            for fn in sorted(files):
                print '\t', fn

    def update_cmake(self):
        deps = self.get_dependencies_from_msgs()
        self.cmake.check_dependencies(self.get_build_dependencies() + deps)

        if CFG.should('check_exported_dependencies'):
            self.cmake.check_exported_dependencies(self.name, self.get_message_dependencies())

        self.cmake.check_generators(self.files['msg'], self.files['srv'], self.files['action'], self.files['cfg'], deps)

        if self.has_header_files():
            self.cmake.check_include_path()

        setup = self.get_setup_py()
        if setup and setup.valid and 'catkin_python_setup' not in self.cmake.content_map:
            self.cmake.add_command_string('catkin_python_setup()')

        if CFG.should('check_installs'):
            self.cmake.update_cplusplus_installs()
            if setup:
                self.cmake.update_python_installs(setup.execs)

            if CFG.should('check_misc_installs'):
                extra_files_by_folder = collections.defaultdict(list)
                the_root = os.path.join(self.root, '')
                for category, files in self.files.iteritems():
                    if category in ['source', 'msg', 'srv', 'action', None]:
                        continue
                    for fn in files:
                        path, base = os.path.split(fn.replace(the_root, '', 1))
                        extra_files_by_folder[path].append(base)

                for folder, files in extra_files_by_folder.iteritems():
                    self.cmake.update_misc_installs(files, folder)

        self.cmake.output()

    def has_header_files(self):
        goal_folder = os.path.join(self.root, 'include', self.name)
        for fn in self.files['source']:
            if goal_folder in fn:
                return True
        return False

    def get_python_source(self):
        sources = []
        for source in self.sources:
            if source.python and 'setup.py' not in source.fn:
                sources.append(source)
        return sources

    def get_setup_py(self):
        sources = self.get_python_source()
        if len(sources) == 0:
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

        pattern = '%s::%s'
        for pkg1, name1, pkg2, name2 in plugins:
            if pkg2 not in self.plugins:
                self.plugins[pkg2] = PluginXML(self.root + '/plugins.xml')
                self.manifest.add_plugin_export('plugins.xml', pkg2)
            self.plugins[pkg2].insert_if_needed(pattern % (pkg1, name1), pattern % (pkg2, name2))

        for config in self.plugins.values():
            config.write()
        self.manifest.output()

    def get_people(self):
        people = {}
        people['maintainers'] = self.manifest.get_people('maintainer')
        people['authors'] = self.manifest.get_people('author')
        return people

    def get_license(self):
        return self.manifest.get_license()

    def update_people(self, replace={}):
        self.manifest.update_people('maintainer', replace)
        self.manifest.update_people('author', replace)

    def set_license(self, license):
        self.manifest.set_license(license)

    def remove_useless(self):
        mainpage_pattern = re.compile(MAINPAGE_S % self.name)
        for fn in self.files[EXTRA]:
            if 'mainpage.dox' in fn:
                s = open(fn).read()
                if mainpage_pattern.match(s):
                    os.remove(fn)

def get_packages(root_fn='.', create_objects=True):
    packages = []
    for root, dirs, files in os.walk(root_fn):
        if '.git' in root:
            continue
        if 'package.xml' in files:
            if create_objects:
                packages.append(Package(root))
            else:
                packages.append(root)
    return packages
