import collections
import rospkg
import os
import stat
import yaml

CONFIG_PATH = os.path.expanduser('~/.ros/roscompile.yaml')
CONFIG = None
PKG_PATH = rospkg.RosPack().get_path('roscompile')

roscompile_functions = collections.OrderedDict()


def roscompile(f):
    roscompile_functions[f.__name__] = f
    return f


def get_ignore_data_helper(basename, add_newline=True):
    fn = os.path.join(PKG_PATH, 'data', basename + '.ignore')
    lines = []
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


def get_config():
    global CONFIG
    if CONFIG is None:
        if os.path.exists(CONFIG_PATH):
            CONFIG = yaml.load(open(CONFIG_PATH))
        else:
            CONFIG = {}
    return CONFIG
