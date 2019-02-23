import os
import sys
import traceback
from package import Package


def get_packages(root_fn='.', create_objects=True):
    packages = []
    for root, dirs, files in os.walk(root_fn):
        if '.git' in root:
            continue
        if 'package.xml' in files:
            if create_objects:
                try:
                    packages.append(Package(root))
                except:
                    sys.stderr.write('ERROR: Trouble parsing package @ %s\n' % root)
                    sys.stderr.write(traceback.format_exc())
            else:
                packages.append(root)
    return packages
