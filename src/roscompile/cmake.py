from collections import defaultdict
import re

BREAKERS = ['catkin_package']
ALL_CAPS = re.compile('^[A-Z_]+$')

def split_comments_and_words(s):
    words = []
    while '#' in s:
        i = s.index('#')
        words += re.split('\s+', s[:i])
        if '\n' in s:
            i2 = s.index('\n', i)
            words.append( s[i:i2+1] )
            s = s[i2+1:]
        else:
            words.append( s[i:] + '\n' )
            s = ''
    words += re.split('\s+', s)        
        
    return words

class Command:
    def __init__(self, cmd, params):
        self.cmd = cmd
        key = ''
        values = []
        self.params = []
        for word in split_comments_and_words(params):
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
            
    def get_section(self, search_key):
        for key, values in self.params:
            if search_key == key:
                return values
        return None        
        
    def __repr__(self, lines=False):
        s = self.cmd + '('
        p = ''
        if lines:
            p += '\n'
        for key, values in self.params:
            if key != '':
                if lines:
                    p += '    '
                elif len(p)>0:
                    p += ' '
                p += key + ' '
                
            p += ' '.join(values)
            if lines and p[-1]!='\n':
                p+='\n'
        
        s += p
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
            
    def package_check(self, pkgs, cmd_name, section_name):        
        for cmd in self.content_map[cmd_name]:
            section = cmd.get_section(section_name)
            if section:
                pkgs = [pkg for pkg in pkgs if pkg not in section]
        section += pkgs
            
    def check_dependencies(self, pkgs):
        self.package_check(pkgs, 'find_package', 'COMPONENTS')
        self.package_check(pkgs, 'catkin_package', 'DEPENDS')

    def add_command(self, name, params):
        cmd = Command(name, params)
        self.contents.append(cmd)
        self.content_map[name].append(cmd)
                    
    def output(self):
        with open(self.fn, 'w') as cmake:
            for x in self.contents:
                if x.__class__==Command:
                    lines = x.cmd in BREAKERS
                    cmake.write(x.__repr__(lines))
                else:    
                    cmake.write(str(x))

