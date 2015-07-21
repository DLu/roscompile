import os
import re

TEMPLATE = """#!/usr/bin/env python

from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup

%(var)s = generate_distutils_setup(
    packages=['%(name)s'],
    package_dir={'': 'src'},
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
        for source in self.files:
            if 'src/%s'%self.name in source.fn:
                self.valid = True
                break

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
        return TEMPLATE % {'name': self.name, 'var': self.var}

