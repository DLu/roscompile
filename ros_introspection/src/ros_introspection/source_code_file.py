import re
import os
from roscompile.resource_list import is_package, is_message, is_service, get_python_dependency

PKG = '([^\.;]+)(\.?[^;]*)?'
PYTHON1 = '^import ' + PKG
PYTHON2 = 'from ' + PKG + ' import .*'
CPLUS = re.compile('#include\s*[<\\"]([^/]*)/?([^/]*)[>\\"]')
ROSCPP = re.compile('#include\s*<ros/ros.h>')

EXPRESSIONS = [re.compile(PYTHON1), re.compile(PYTHON2), CPLUS]

PLUGIN_PATTERN = 'PLUGINLIB_EXPORT_CLASS\(([^:]+)::([^,]+), ([^:]+)::([^,]+)\)'
PLUGIN_RE = re.compile(PLUGIN_PATTERN)

class Source:
    def __init__(self, fn, root=None):
        self.fn = fn
        if root:
            self.rel_fn = fn.replace(root + '/', '')
        else:
            self.rel_fn = fn
        self.lines = map(str.strip, open(fn, 'r').readlines())
        self.python = '.py' in self.fn or (len(self.lines) > 0 and 'python' in self.lines[0])
        self.tags = set()

    def get_import_packages(self):
        pkgs = set()
        for line in self.lines:
            for EXP in EXPRESSIONS:
                m = EXP.search(line)
                if m:
                    pkgs.add(m.group(1))
            if ROSCPP.search(line):
                pkgs.add('roscpp')
        return sorted(list(pkgs))

    def get_dependencies(self):
        deps = []
        for pkg in self.get_import_packages():
            if is_package(pkg):
                deps.append(pkg)
        return deps

    def get_external_python_dependencies(self):
        deps = []
        if not self.python:
            return deps

        for pkg in self.get_import_packages():
            p_dep = get_python_dependency(pkg)
            if p_dep:
                deps.append(p_dep)
        return deps

    def get_message_dependencies(self):
        d = set()
        for line in self.lines:
            m = CPLUS.search(line)
            if m:
                pkg, name = m.groups()
                if len(name) == 0 or name[-2:] != '.h':
                    continue
                name = name.replace('.h', '')
                if is_message(pkg, name) or is_service(pkg, name):
                    d.add(pkg)
        return sorted(list(d))

    def get_plugins(self):
        a = []
        for line in self.lines:
            m = PLUGIN_RE.search(line)
            if m:
                a.append(m.groups())
        return a

    def is_executable(self):
        return os.access(self.fn, os.X_OK)

    def __repr__(self):
        return self.fn
