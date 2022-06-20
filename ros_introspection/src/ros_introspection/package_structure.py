import collections
import os

from .source_code_file import is_python_hashbang_line

KEY = ['package.xml', 'CMakeLists.txt', 'setup.py']
SRC_EXTS = ['.py', '.cpp', '.h', '.hpp', '.c', '.cc']
GENERATORS = ['.msg', '.srv', '.action']


def get_filetype_by_contents(filename, ext):
    with open(filename) as f:
        try:
            first_line = f.readline()
        except UnicodeDecodeError:
            return
        if is_python_hashbang_line(first_line):
            return 'source'
        elif '<launch' in first_line:
            return 'launch'
        elif ext == '.xml' and ('<library' in first_line or '<class_libraries' in first_line):
            return 'plugin_config'


def get_package_structure(pkg_root):
    structure = collections.defaultdict(dict)

    for root, dirs, files in os.walk(pkg_root):
        if '.git' in root or '.svn' in root:
            continue
        for fn in files:
            ext = os.path.splitext(fn)[-1]
            full = '%s/%s' % (root, fn)
            rel_fn = full.replace(pkg_root + '/', '')

            if fn[-1] == '~' or fn[-4:] == '.pyc':
                continue
            if fn in KEY:
                structure['key'][rel_fn] = full
            elif ext == '.launch':
                structure['launch'][rel_fn] = full
            elif ext in SRC_EXTS:
                structure['source'][rel_fn] = full
            elif ext in GENERATORS:
                structure['generators'][rel_fn] = full
            elif ext == '.cfg' and 'cfg/' in full:
                structure['cfg'][rel_fn] = full
            elif ext in ['.urdf', '.xacro']:
                structure['urdf'][rel_fn] = full
            else:
                structure[get_filetype_by_contents(full, ext)][rel_fn] = full
    return structure
