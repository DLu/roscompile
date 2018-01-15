import os
from package import Package


def get_packages(root_fn='.', create_objects=True):
    packages = []
    for root, dirs, files in os.walk(root_fn):
        if '.git' in root:
            continue
        if 'package.xml' in files:
            if create_objects:
                packages.append(Package(root))
            else:
                packages.append(root)
    return packages
