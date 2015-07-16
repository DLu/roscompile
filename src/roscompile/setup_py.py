import os

TEMPLATE = """#!/usr/bin/env python

from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup

package_info = generate_distutils_setup(
%s)

setup(**package_info)
"""

PACKAGES = "    packages=['%s'],\n"
PDIR = "    package_dir={'': 'src'},\n"

class SetupPy:
    def __init__(self, name, root, files):
        self.root = root
        self.name = name
        self.files = files
        
        self.valid = False
        for source in self.files:
            if 'src/%s'%self.name in source.fn:
                self.valid = True
                break

    def write_if_needed(self):
        if not self.valid:
            return
        fn = self.root + '/setup.py'
        output = str(self)
        if os.path.exists(fn):
            original = open(fn, 'r').read()
            if original == output:
                return
        print "    Writing setup.py"   
        with open(fn, 'w') as f:
            f.write(output)
        
        
    def __repr__(self):
        s1 = PACKAGES%self.name
        s1 += PDIR
        return TEMPLATE % s1

