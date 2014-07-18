import re
import subprocess

PKG = '([^\.;]+)(\.?[^;]*)?'
PYTHON1 = '^import ' + PKG
PYTHON2 = 'from ' + PKG + ' import .*'

EXPRESSIONS = [re.compile(PYTHON1), re.compile(PYTHON2)]

def get_root(package):
    p = subprocess.Popen(['rospack', 'find', package], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out.strip()

class Source:
    def __init__(self, fn):
        self.lines = map(str.strip, open(fn, 'r').readlines())

    def get_dependencies(self):
        d = set()
        for line in self.lines:
            for EXP in EXPRESSIONS:
                m = EXP.search(line)
                if m:
                    if get_root( m.group(1) ):
                        d.add(m.group(1))
        return sorted(list(d))

