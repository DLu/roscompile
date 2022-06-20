import collections
import os
import re
import stat

import rospkg

import yaml

CONFIG_PATH = os.path.expanduser('~/.ros/roscompile.yaml')
CONFIG = None
PKG_PATH = rospkg.RosPack().get_path('roscompile')
TRAILING_PATTERN = re.compile(r'^(.*[^\w])\w+\n$')

roscompile_functions = collections.OrderedDict()


def roscompile(f):
    roscompile_functions[f.__name__] = f
    return f


def get_ignore_data_helper(basename, add_newline=True):
    fn = os.path.join(PKG_PATH, 'data', basename + '.ignore')
    lines = []
    if not os.path.exists(fn):
        return lines
    for s in open(fn):
        if s == '\n':
            continue
        if add_newline:
            lines.append(s)
        else:
            lines.append(s[:-1])
    return lines


def get_ignore_data(name, variables=None, add_newline=True):
    ignore_lines = get_ignore_data_helper(name, add_newline)
    if not variables:
        return ignore_lines
    for pattern in get_ignore_data_helper(name + '_patterns', add_newline):
        ignore_lines.append(pattern % variables)
    return ignore_lines


def make_executable(fn):
    existing_permissions = stat.S_IMODE(os.lstat(fn).st_mode)
    os.chmod(fn, existing_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def make_not_executable(fn):
    existing_permissions = stat.S_IMODE(os.lstat(fn).st_mode)
    os.chmod(fn, existing_permissions | ~stat.S_IXUSR | ~stat.S_IXGRP | ~stat.S_IXOTH)


def get_config():
    global CONFIG
    if CONFIG is None:
        if os.path.exists(CONFIG_PATH):
            CONFIG = yaml.safe_load(open(CONFIG_PATH))
        else:
            CONFIG = {}
    return CONFIG


def convert_to_underscore_notation(name):
    # https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def convert_to_caps_notation(name):
    return ''.join([x.title() for x in name.split('_')])
