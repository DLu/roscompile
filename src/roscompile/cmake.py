class CMake:
    def __init__(self, fn):
        self.fn = fn
        self.contents = []
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
                    self.contents.append( (s, params) )
                    s = ''
                    params = ''
                    state = 0
                else:
                    params += c
        if len(s)>0:
            self.contents.append(s)
        print self.contents
                    
    def output(self):
        with open(self.fn, 'w') as cmake:
            for x in self.contents:
                if type(x)==str:
                    cmake.write(x)
                else:
                    fne, params = x
                    cmake.write('%s(%s)'%(fne, params))
