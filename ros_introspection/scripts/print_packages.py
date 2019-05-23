#!/usr/bin/python

from ros_introspection.util import get_packages

for package in get_packages():
    print(package)
