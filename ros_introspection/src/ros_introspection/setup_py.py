import os
import re

VAR_PATTERN = re.compile(r'\*\*([\w_]+)\)')
EQ_PATTERN = re.compile(r'([\w_]+)\s*=([^,]+)')

EXEC_TEMPLATE = """
    scripts=%s,"""

TEMPLATE = """#!/usr/bin/env python

from %(import_pkg)s import setup
from catkin_pkg.python_setup import generate_distutils_setup

%(var)s = generate_distutils_setup(
    packages=['%(name)s'],%(exec)s
    package_dir={'': 'src'}
)

setup(**%(var)s)
"""


class SetupPy:
    def __init__(self, pkg_name, file_path):
        self.pkg_name = pkg_name
        self.file_path = file_path
        self.var = 'package_info'
        self.execs = []

        if os.path.exists(self.file_path):
            self.changed = False
            original = open(self.file_path, 'r').read()

            # Determine Setuptools or Distutils
            self.noetic = 'distutils.core' not in original

            # Determine variable name
            m = VAR_PATTERN.search(original)
            if m:
                self.var = m.group(1)

            # Parse generate_distutils_setup
            key_s = 'generate_distutils_setup'
            if key_s not in original:
                return
            i = original.index(key_s) + len(key_s)
            p_i = original.index('(', i)
            ep_i = original.index(')', p_i)
            body = original[p_i + 1:ep_i]
            for var_name, value in EQ_PATTERN.findall(body):
                if var_name == 'scripts':
                    self.execs = eval(value)
        else:
            self.changed = True
            self.noetic = False

    def write(self):
        if not self.changed:
            return
        with open(self.file_path, 'w') as f:
            f.write(str(self))

    def __repr__(self):
        if len(self.execs) > 0:
            execs = EXEC_TEMPLATE % repr(self.execs)
        else:
            execs = ''

        params = {'name': self.pkg_name, 'var': self.var, 'exec': execs}
        if self.noetic:
            params['import_pkg'] = 'setuptools'
        else:
            params['import_pkg'] = 'distutils.core'
        return TEMPLATE % params
