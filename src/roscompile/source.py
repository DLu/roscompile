import re
from roscompile.package_list import is_package

PKG = '([^\.;]+)(\.?[^;]*)?'
PYTHON1 = '^import ' + PKG
PYTHON2 = 'from ' + PKG + ' import .*'
CPLUS = '#include\s*[<\\"]([^/]*)/?([^/]*)[>\\"]'

EXPRESSIONS = [re.compile(PYTHON1), re.compile(PYTHON2), re.compile(CPLUS)]

class Source:
    def __init__(self, fn):
        self.fn = fn
        self.lines = map(str.strip, open(fn, 'r').readlines())
        self.python = '.py' in self.fn or (len(self.lines)>0 and 'python' in self.lines[0])  
        
    def get_dependencies(self):
        d = set()
        for line in self.lines:
            for EXP in EXPRESSIONS:
                m = EXP.search(line)
                if m:
                    if is_package( m.group(1) ):
                        d.add(m.group(1))
        return sorted(list(d))

    def __repr__(self):
        return self.fn
