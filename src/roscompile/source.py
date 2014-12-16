import re
import subprocess

PKG = '([^\.;]+)(\.?[^;]*)?'
PYTHON1 = '^import ' + PKG
PYTHON2 = 'from ' + PKG + ' import .*'
CPLUS = '#include\s*[<\\"]([^/]*)/?([^/]*)[>\\"]'

EXPRESSIONS = [re.compile(PYTHON1), re.compile(PYTHON2), re.compile(CPLUS)]

PLUGIN_PATTERN = 'PLUGINLIB_EXPORT_CLASS\(([^:]+)::([^,]+), ([^:]+)::([^,]+)\)'
PLUGIN_RE = re.compile(PLUGIN_PATTERN)

def get_root(package):
    p = subprocess.Popen(['rospack', 'find', package], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out.strip()

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
                    if get_root( m.group(1) ):
                        d.add(m.group(1))
        return sorted(list(d))
        
    def get_plugins(self):
        a = []
        for line in self.lines:
            m = PLUGIN_RE.search(line)
            if m:
                a.append( m.groups() )
        return a

    def __repr__(self):
        return self.fn
