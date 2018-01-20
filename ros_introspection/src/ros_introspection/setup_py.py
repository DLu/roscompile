import os
import re

VAR_PATTERN = re.compile('\*\*([\w_]+)\)')
EQ_PATTERN = re.compile('([\w_]+)\s*=([^,]+)')

EXEC_TEMPLATE = """
    scripts=%s,"""

TEMPLATE = """#!/usr/bin/env python

from distutils.core import setup
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
            original = open(self.file_path, 'r').read()

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

    def write(self):
        with open(self.file_path, 'w') as f:
            f.write(str(self))

    def __repr__(self):
        if len(self.execs) > 0:
            execs = EXEC_TEMPLATE % repr(self.execs)
        else:
            execs = ''
        return TEMPLATE % {'name': self.pkg_name, 'var': self.var, 'exec': execs}
