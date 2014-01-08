import os
import os.path
import collections
from roscompile.launch import Launch 

SRC_EXTS = ['.py', '.cpp', '.h']
CONFIG_EXTS = ['.yaml', '.rviz']
DATA_EXTS = ['.dae', '.jpg', '.stl', '.png']
MODEL_EXTS = ['.urdf', '.xacro', '.srdf']

EXTS = {'source': SRC_EXTS, 'config': CONFIG_EXTS, 'data': DATA_EXTS, 'model': MODEL_EXTS}
BASIC = ['package.xml', 'CMakeLists.txt']
SIMPLE = ['.launch', '.msg', '.srv', '.action', '.cfg']

def match(ext):
    for name, exts in EXTS.iteritems():
        if ext in exts:
            return name
    return None

class Package:
    def __init__(self, root):
        self.root = root
        self.name = os.path.split(root)[-1]

    def sort_files(self, print_extras=False):
        data = collections.defaultdict(list)
        for root,dirs,files in os.walk(self.root):
            extras = []
            for fn in files:
                ext = os.path.splitext(fn)[-1]
                full = '%s/%s'%(root, fn)
                if fn[-1]=='~':
                    continue
                ext_match = match(ext)

                if ext_match:
                    data[ext_match].append(full)
                elif ext in SIMPLE:
                    name = ext[1:]
                    data[name].append(full)
                elif fn in BASIC:
                    data[None].append(full)
                else:
                    extras.append(full)
            if print_extras and len(extras)>0:
                print '  ', root
                for fn in extras:
                    print '    ', fn

        return data

    def get_dependencies(self):
        files = self.sort_files()
        packages = set()
        for launch in files['launch']:
            x = Launch(launch)
            packages.update(x.get_dependencies())
        if self.name in packages:
            packages.remove(self.name)
        return sorted(list(packages))



def get_packages(root_fn='.'):
    packages = []
    for root,dirs,files in os.walk(root_fn):
        if '.git' in root:
            continue
        if 'package.xml' in files:
            packages.append(Package(root))
    return packages

