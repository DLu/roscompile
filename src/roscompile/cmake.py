from collections import defaultdict
import re
import os.path

BREAKERS = ['catkin_package']
ALL_CAPS = re.compile('^[A-Z_]+$')

ORDERING = ['cmake_minimum_required', 'project', 'find_package', 
            'add_message_files', 'add_service_files', 'add_action_files', 
            'generate_messages', 'catkin_package', 
            ['add_library', 'add_executable', 'target_link_libraries'],
            'catkin_add_gtest', 'install']

def get_ordering_index(cmd):
    for i, o in enumerate(ORDERING):
        if type(o)==list:
            if cmd in o:
                return i
        elif cmd==o:
            return i
    return len(ORDERING)                


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

    def add_section(self, key, values=[]):
        self.params.append( (key, values) )
        
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
            
    def section_check(self, items, cmd_name, section_name):        
        if len(items)==0:
            return
            
        if cmd_name not in self.content_map:
            params = section_name + ' '  + ' '.join(items)
            self.add_command(cmd_name, params)
            print 'Adding new %s command to CMakeLists.txt with %s' % (cmd_name, params)
            return    
            
        section = None
        for cmd in self.content_map[cmd_name]:
            section = cmd.get_section(section_name)
            if section:
                items = [item for item in items if item not in section]
        if len(items)==0:
            return        
        if section:        
            section += items
        else:
            cmd.add_section(section_name, items)
        print 'Adding %s to the %s/%s section of your CMakeLists.txt'%(str(items), cmd_name, section_name)
            
    def check_dependencies(self, pkgs):
        self.section_check(pkgs, 'find_package', 'COMPONENTS')
        self.section_check(pkgs, 'catkin_package', 'DEPENDS')
        
    def check_generators(self, msgs, srvs, actions):
        self.section_check( map(os.path.basename, msgs), 'add_message_files', 'FILES')
        self.section_check( map(os.path.basename, srvs), 'add_service_files', 'FILES')
        self.section_check( map(os.path.basename, actions), 'add_action_files', 'FILES')
        
        if len(msgs)+len(srvs)+len(actions) > 0:
            self.section_check(['message_generation'], 'find_package', 'COMPONENTS')
            self.section_check(['message_runtime'], 'catkin_package', 'CATKIN_DEPENDS')

    def add_command(self, name, params):
        cmd = Command(name, params)
        self.contents.append(cmd)
        self.content_map[name].append(cmd)

    def enforce_ordering(self):
        chunks = []
        current = []
        for x in self.contents:
            current.append(x)
            if x.__class__==Command:
                chunks.append( (x.cmd, current) )
                current = []
        if len(current)>0:
            chunks.append( (None, current) )
        
        self.contents = []
            
        for a,b in sorted(chunks, key=lambda d: get_ordering_index(d[0])):
            self.contents += b

    def output(self):
        self.enforce_ordering()
        with open(self.fn, 'w') as cmake:
            for x in self.contents:
                if x.__class__==Command:
                    lines = x.cmd in BREAKERS
                    cmake.write(x.__repr__(lines))
                else:    
                    cmake.write(str(x))

