import collections
from package_structure import get_package_structure
from package_xml import PackageXML
from cmake_parser import parse_file
from source_code import SourceCode
from ros_generator import ROSGenerator
from setup_py import SetupPy
from launch import Launch
from plugin_xml import PluginXML


class Package:
    def __init__(self, root):
        self.root = root
        self.manifest = PackageXML(self.root + '/package.xml')
        self.name = self.manifest.name
        self.cmake = parse_file(self.root + '/CMakeLists.txt')

        package_structure = get_package_structure(root)
        self.source_code = SourceCode(package_structure['source'], self.name)
        self.source_code.setup_tags(self.cmake)

        self.launches = []
        self.plugin_configs = []
        for rel_fn, file_path in package_structure['launch'].iteritems():
            self.launches.append(Launch(rel_fn, file_path))
        for rel_fn, file_path in package_structure['plugin_config'].iteritems():
            self.plugin_configs.append(PluginXML(rel_fn, file_path))

        self.setup_py = None
        if 'setup.py' in package_structure['key']:
            self.setup_py = SetupPy(self.name, package_structure['key']['setup.py'])
        self.generators = collections.defaultdict(list)
        for rel_fn, path in package_structure['generators'].iteritems():
            gen = ROSGenerator(rel_fn, path)
            self.generators[gen.type].append(gen)
        self.dynamic_reconfigs = package_structure['cfg'].keys()
        self.misc_files = package_structure[None].keys()

    def get_build_dependencies(self):
        return self.source_code.get_build_dependencies()

    def get_run_dependencies(self):
        packages = set()
        for launch in self.launches:
            if launch.test:
                continue
            packages.update(launch.get_dependencies())

        packages.update(self.source_code.get_external_python_dependencies())
        if self.name in packages:
            packages.remove(self.name)
        return packages

    def get_test_dependencies(self):
        packages = set()
        packages.update(self.source_code.get_test_dependencies())
        for launch in self.launches:
            if not launch.test:
                continue
            packages.add('rostest')
            packages.update(launch.get_dependencies())
        if self.name in packages:
            packages.remove(self.name)
        return packages

    def get_all_generators(self):
        for gens in self.generators.values():
            for gen in gens:
                yield gen

    def get_dependencies_from_msgs(self):
        packages = set()
        for gen in self.get_all_generators():
            packages.update(gen.dependencies)
        return packages

    def write(self):
        self.manifest.write()
        self.cmake.write()
        for plugin_config in self.plugin_configs:
            plugin_config.write()
        if self.setup_py:
            self.setup_py.write()
        for gen in self.get_all_generators():
            gen.write()
        for src in self.source_code.sources.values():
            src.write()

    def __repr__(self):
        s = '== {} ========\n'.format(self.name)
        s += '  package.xml\n'
        s += '  CMakeLists.txt\n'
        if self.setup_py:
            s += '  setup.py\n'
        components = {'source': str(self.source_code),
                      'launch': '\n'.join(map(str, self.launches)),
                      'dynamic reconfigure configs': '\n'.join(self.dynamic_reconfigs),
                      'plugin configs': '\n'.join([cfg.rel_fn for cfg in self.plugin_configs]),
                      '{misc}': '\n'.join(self.misc_files)
                      }
        for ext in self.generators:
            components[ext] = '\n'.join(map(str, self.generators[ext]))
        for name, c_str in sorted(components.iteritems()):
            if len(c_str) == 0:
                continue
            s += '  {}\n'.format(name)
            for line in c_str.split('\n'):
                s += '    ' + line + '\n'
        return s
