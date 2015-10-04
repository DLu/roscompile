import os
import re

EXEC_TEMPLATE = """
    scripts=[%s],"""

TEMPLATE = """#!/usr/bin/env python

from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup

%(var)s = generate_distutils_setup(
    packages=['%(name)s'],%(exec)s
    package_dir={'': 'src'}
)

setup(**%(var)s)
"""

VAR_PATTERN = re.compile('\*\*([\w_]+)\)')

class SetupPy:
    def __init__(self, name, root, files):
        self.root = root
        self.name = name
        self.files = files
        self.var = 'package_info'
        
        self.valid = False
        self.execs = []
        for source in self.files:
            if 'src/%s'%self.name in source.fn:
                self.valid = True
            if source.is_executable() and '.cfg'!=source.fn[-4:]:
                self.execs.append(source.rel_fn)

    def write_if_needed(self):
        if not self.valid:
            return
        fn = self.root + '/setup.py'
        
        if os.path.exists(fn):
            original = open(fn, 'r').read()
            m = VAR_PATTERN.search(original)
            if m:
                self.var = m.group(1)
                
            output = str(self)
            if original == output:
                return
        else:
            output = str(self)
            
        print "    Writing setup.py"   
        with open(fn, 'w') as f:
            f.write(output)
        
        
    def __repr__(self):
        if len(self.execs)>0:
            execs = EXEC_TEMPLATE % ', '.join(["'%s'"%s for s in self.execs])
        else:
            execs = ''
        return TEMPLATE % {'name': self.name, 'var': self.var, 'exec': execs}

