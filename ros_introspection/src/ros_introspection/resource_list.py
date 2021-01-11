import datetime
import os

import requests

from rosmsg import list_types

import rospkg

import yaml

DOT_ROS_FOLDER = os.path.expanduser('~/.ros')
PY_DEP_FILENAME = os.path.join(DOT_ROS_FOLDER, 'py_deps.yaml')

PYTHON_DEPS = {}


def maybe_download_python_deps():
    global PYTHON_DEPS
    if os.path.exists(PY_DEP_FILENAME):
        PYTHON_DEPS = yaml.safe_load(open(PY_DEP_FILENAME))
        if 'last_download' in PYTHON_DEPS:
            now = datetime.datetime.now()
            if now - PYTHON_DEPS['last_download'] < datetime.timedelta(days=3):
                return

    try:
        ff = requests.get('https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/python.yaml').text
    except requests.exceptions.ConnectionError:
        print('Cannot retrieve latest python dependencies')
        return

    PYTHON_DEPS = yaml.safe_load(ff)
    PYTHON_DEPS['last_download'] = datetime.datetime.now()

    if not os.path.exists(DOT_ROS_FOLDER):
        os.mkdir(DOT_ROS_FOLDER)
    yaml.dump(PYTHON_DEPS, open(PY_DEP_FILENAME, 'w'))


def get_python_dependency(key):
    for var in [key, 'python-' + key, 'python3-' + key, key.replace('python-', 'python3-'), key.replace('python-', ''),
                key.replace('python-', '').replace('-', '_')]:
        if var in PYTHON_DEPS:
            return var


maybe_download_python_deps()


PACKAGES = set()
MESSAGES = set()
SERVICES = set()

rospack = rospkg.RosPack()
for pkg in rospack.list():
    PACKAGES.add(pkg)
    for mode, ros_set in [('.msg', MESSAGES), ('.srv', SERVICES)]:
        for gen_key in list_types(pkg, mode, rospack):
            pkg, gen = gen_key.split('/')
            ros_set.add((pkg, gen))


def is_package(pkg):
    return pkg in PACKAGES


def is_message(pkg, msg):
    return (pkg, msg) in MESSAGES


def is_service(pkg, srv):
    return (pkg, srv) in SERVICES
