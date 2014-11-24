from collections import defaultdict
import re

ALL_CAPS = re.compile('[A-Z_]+')

class Command:
    def __init__(self, cmd, params):
        self.cmd = cmd
        key = ''
        values = []
        self.params = []
        for word in re.split('\s+', params):
            if not ALL_CAPS.match(word):
                if len(word) > 0:
                    values.append(word)
            else:
                if len(values)>0 or len(key)>0:
                    self.params.append( (key, values) )
                key = word
                values = []
        if len(values)>0 or len(key)>0:
            self.params.append( (key, values) )
        
    def __repr__(self):
        s = self.cmd + '('
        p = ''
        for key, values in self.params:
            if key != '':
                p += ' ' + key + ' '
                
            p += ' '.join(values)
        s += p.strip()
        
        return s + ')'

class CMake:
    def __init__(self, fn):
        self.fn = fn
        self.contents = []
        self.content_map = defaultdict(list)
        original = open(fn).read()
        state = 0
        s = ''
        params = ''
        
        for c in original:
            if state == 0:
                if c.isspace():
                    s += c
                elif c=='#':
                    state = 1
                    s += c
                else:
                    if len(s)>0:
                        self.contents.append(s)
                    state = 2
                    s = c
            elif state == 1:
                s += c
                if c=='\n':
                    state = 0
            elif state == 2:
                if c == '(':
                    state = 3
                
                else:
                    s += c
            elif state == 3:
                if c == ')':
                    cmd = Command(s,params)
                    self.contents.append( cmd )
                    self.content_map[s].append(cmd)
                    s = ''
                    params = ''
                    state = 0
                else:
                    params += c
        if len(s)>0:
            self.contents.append(s)
                    
    def output(self):
        with open(self.fn, 'w') as cmake:
            for x in self.contents:
                cmake.write(str(x))

