from collections import defaultdict

class Command:
    def __init__(self, cmd, params):
        self.cmd = cmd
        self.params = params
        
    def __repr__(self):
        return '%s(%s)'%(self.cmd, str(self.params))

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

