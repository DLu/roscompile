import os
import yaml
import subprocess
import datetime
import resource_retriever

DOT_ROS_FOLDER = os.path.expanduser('~/.ros')
PY_DEP_FILENAME = os.path.join(DOT_ROS_FOLDER, 'py_deps.yaml')

PYTHON_DEPS = {}


def maybe_download_python_deps():
    global PYTHON_DEPS
    if os.path.exists(PY_DEP_FILENAME):
        PYTHON_DEPS = yaml.load(open(PY_DEP_FILENAME))
        if 'last_download' in PYTHON_DEPS:
            now = datetime.datetime.now()
            if now - PYTHON_DEPS['last_download'] < datetime.timedelta(days=3):
                return

    ff = resource_retriever.get('https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/python.yaml')
    PYTHON_DEPS = yaml.load(ff)
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


def get_output_lines(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return [s for s in out.split('\n') if len(s) > 0]


PACKAGES = {}
MESSAGES = set()
SERVICES = set()

for line in get_output_lines(['rospack', 'list']):
    pkg, folder = line.split()
    PACKAGES[pkg] = folder

for line in get_output_lines(['rosmsg', 'list']):
    pkg, msg = line.split('/')
    MESSAGES.add((pkg, msg))

for line in get_output_lines(['rossrv', 'list']):
    pkg, srv = line.split('/')
    SERVICES.add((pkg, srv))


def is_package(pkg):
    return pkg in PACKAGES


def is_message(pkg, msg):
    return (pkg, msg) in MESSAGES


def is_service(pkg, srv):
    return (pkg, srv) in SERVICES
