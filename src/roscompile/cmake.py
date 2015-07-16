from collections import defaultdict, OrderedDict
import re
import os.path
from resource_retriever import get

BREAKERS = ['catkin_package']
ALL_CAPS = re.compile('^[A-Z_]+$')
IGNORE_LINES = [s + '\n' for s in get('package://roscompile/data/cmake.ignore').read().split('\n') if len(s)>0]

ORDERING = ['cmake_minimum_required', 'project', 'find_package', 'add_definitions',
            'add_message_files', 'add_service_files', 'add_action_files', 'generate_dynamic_reconfigure_options',
            'generate_messages', 'catkin_package', 
            ['add_library', 'add_executable', 'target_link_libraries', 'add_dependencies', 'include_directories'],
            'catkin_add_gtest', 'group', 'install']

def get_ordering_index(cmd):
    for i, o in enumerate(ORDERING):
        if type(o)==list:
            if cmd in o:
                return i
        elif cmd==o:
            return i
    print '\tUnsure of ordering for', cmd        
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
    
class Section:
    def __init__(self, name='', values=None):
        self.name = name
        if values is None:
            self.values = []
        else:    
            self.values = values
        
    def add(self, v):
        self.values.append(v)
        
    def is_valid(self):
        return len(self.name)>0 or len(self.values)>0    
        
    def __repr__(self):
        s = ''
        if len(self.name)>0:
            s = self.name
            if len(self.values)>0:
                s += ' '
        s += ' '.join(self.values)
        return s

class Command:
    def __init__(self, cmd, params):
        self.cmd = cmd
        self.joiner = '\n    ' if '\n' in params else ' '
        sections = []        
        sect = Section()
        sections.append(sect)


        for word in split_comments_and_words(params):
            if len(word)==0:
                continue
            if ALL_CAPS.match(word):
                sect = Section(word)
                sections.append(sect)
            else:
                sect.add(word)
                
        self.sections = OrderedDict()
        for sect in sections:
            if sect.is_valid():
                self.sections[sect.name] = sect
            
    def get_section(self, key):
        return self.sections.get(key, None)

    def add_section(self, key, values=[]):
        self.sections[key] = Section(key, values)
        
    def __repr__(self):
        s = self.cmd + '('
        s += self.joiner.join(map(str,self.sections.values()))
        if '\n' in s:
            s += '\n'
        s += ')'
        return s

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
            print '\tAdding new %s command to CMakeLists.txt with %s' % (cmd_name, params)
            return    
            
        section = None
        for cmd in self.content_map[cmd_name]:
            s = cmd.get_section(section_name)
            if s:
                if section is None:
                    section = s
                items = [item for item in items if item not in s.values]
        if len(items)==0:
            return        
        if section:        
            section.values += items
        else:
            cmd.add_section(section_name, items)
        print '\tAdding %s to the %s/%s section of your CMakeLists.txt'%(str(items), cmd_name, section_name)
            
    def check_dependencies(self, pkgs):
        self.section_check(pkgs, 'find_package', 'COMPONENTS')
        self.section_check(pkgs, 'catkin_package', 'DEPENDS')
        
    def check_generators(self, msgs, srvs, actions, cfgs):
        self.section_check( map(os.path.basename, msgs), 'add_message_files', 'FILES')
        self.section_check( map(os.path.basename, srvs), 'add_service_files', 'FILES')
        self.section_check( map(os.path.basename, actions), 'add_action_files', 'FILES')
        
        if len(msgs)+len(srvs)+len(actions) > 0:
            self.section_check(['message_generation'], 'find_package', 'COMPONENTS')
            self.section_check(['message_runtime'], 'catkin_package', 'CATKIN_DEPENDS')
        
        cfgs = ['cfg/' + os.path.basename(cfg) for cfg in cfgs]    
        self.section_check( cfgs, 'generate_dynamic_reconfigure_options', '')
        if len(cfgs)>0:
            self.section_check(['dynamic_reconfigure'], 'find_package', 'COMPONENTS')

    def add_command(self, name, params):
        cmd = Command(name, params)
        self.contents.append(cmd)
        self.content_map[name].append(cmd)

    def enforce_ordering(self):
        chunks = []
        current = []
        group = None
        for x in self.contents:
            current.append(x)
            if x.__class__==Command:
                if x.cmd == 'if':
                    group = 'endif'
                elif x.cmd == group:
                    chunks.append( ('group', current))
                    current = []
                    group = None
                elif group is None:    
                    chunks.append( (x.cmd, current) )
                    current = []
        if len(current)>0:
            chunks.append( (None, current) )
        
        self.contents = []
            
        for a,b in sorted(chunks, key=lambda d: get_ordering_index(d[0])):
            self.contents += b

    def __repr__(self):
        return ''.join(map(str, self.contents))

    def output(self, remove_dumb_comments=True):
        self.enforce_ordering()
        
        s = str(self)
        
        if remove_dumb_comments:    
            for line in IGNORE_LINES:
                s = s.replace(line, '')
            while '\n\n\n' in s:    
                s = s.replace('\n\n\n', '\n\n')    
        
        with open(self.fn, 'w') as cmake:
            cmake.write(s)

