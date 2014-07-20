
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
        
    def write(self):
        f = open(self.root + '/setup.py', 'w')
        s1 = PACKAGES%self.name
        
        for source in self.files:
            if 'src' in source.fn:
                s1 += PDIR
                break
        
        f.write( TEMPLATE % s1 )
        f.close()

