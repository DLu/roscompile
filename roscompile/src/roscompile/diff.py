#!/usr/bin/python

from ros_introspection.package import Package
from .terminal import color_header, color_diff
import collections
import tempfile
import shutil
import os
import difflib
from filecmp import dircmp


def get_diff_helper(dcmp, folder=''):
    D = collections.defaultdict(list)
    for name in dcmp.diff_files:
        D['diff'].append(os.path.join(folder, name))
    for name in dcmp.left_only:
        D['deleted'].append(os.path.join(folder, name))
    for name in dcmp.right_only:
        D['added'].append(os.path.join(folder, name))

    for sub_dcmp in dcmp.subdirs.values():
        sub_f = sub_dcmp.left.replace(dcmp.left, '')
        if sub_f[0] == '/':
            sub_f = sub_f[1:]
        D2 = get_diff_helper(sub_dcmp, os.path.join(folder, sub_f))
        for key in D2:
            D[key] += D2[key]
    return dict(D)


def get_diff(original_folder, new_folder):
    dcmp = dircmp(original_folder, new_folder)
    return get_diff_helper(dcmp)


def get_lines(folder, filename):
    return open(os.path.join(folder, filename)).readlines()


def print_diff(filename, left_folder=None, right_folder=None):
    if left_folder is None:
        left = []
    else:
        left = get_lines(left_folder, filename)

    if right_folder is None:
        right = []
    else:
        right = get_lines(right_folder, filename)

    diff = difflib.unified_diff(left, right, fromfile=filename, tofile='%s (modified)' % filename)
    print(''.join(color_diff(diff)))


def preview_changes(package, fn_name, fne):
    try:
        temp_dir = tempfile.mkdtemp()
        new_package_root = os.path.join(temp_dir, package.name)
        shutil.copytree(package.root, new_package_root)
        new_pkg = Package(new_package_root)
        fne(new_pkg)
        new_pkg.write()
        the_diff = get_diff(package.root, new_package_root)
        if len(the_diff) == 0:
            return False

        print color_header(fn_name)

        for filename in the_diff.get('diff', []):
            print_diff(filename, package.root, new_package_root)
        for filename in the_diff.get('deleted', []):
            print_diff(filename, left_folder=package.root)
        for filename in the_diff.get('added', []):
            print_diff(filename, right_folder=new_package_root)
    finally:
        shutil.rmtree(new_package_root)
        shutil.copytree(package.root, new_package_root)
        shutil.rmtree(temp_dir)
    return True
