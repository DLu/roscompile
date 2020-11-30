import os
import os.path
import sys
import traceback

from .package import Package


def get_packages(root_fn='.', create_objects=True):
    packages = []
    for root, dirs, files in sorted(os.walk(root_fn)):
        if '.git' in root:
            continue
        if 'package.xml' in files:
            if create_objects:
                try:
                    packages.append(Package(root))
                except Exception:
                    sys.stderr.write('ERROR: Trouble parsing package @ %s\n' % root)
                    sys.stderr.write(traceback.format_exc())
            else:
                packages.append(root)
    return packages


def get_sibling_packages(package):
    parent_path = os.path.abspath(os.path.join(package.root, '..'))

    sibling_packages = set()
    for sub_package in get_packages(parent_path, create_objects=False):
        pkg_name = os.path.split(sub_package)[1]
        if pkg_name != package.name:
            sibling_packages.add(pkg_name)
    return sibling_packages
