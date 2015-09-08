from collections import defaultdict, OrderedDict
import re
import os.path
from resource_retriever import get
from roscompile.config import CFG

BREAKERS = ['catkin_package']
ALL_CAPS = re.compile('^[A-Z_]+$')
IGNORE_LINES = [s + '\n' for s in get('package://roscompile/data/cmake.ignore').read().split('\n') if len(s)>0]
IGNORE_PATTERNS = [s + '\n' for s in get('package://roscompile/data/cmake_patterns.ignore').read().split('\n') if len(s)>0]

ORDERING = ['cmake_minimum_required', 'project', 'find_package', 'catkin_python_setup', 'add_definitions',
            'add_message_files', 'add_service_files', 'add_action_files', 'generate_dynamic_reconfigure_options',
            'generate_messages', 'catkin_package', 
            ['add_library', 'add_executable', 'target_link_libraries', 'add_dependencies', 'include_directories'],
            'catkin_add_gtest', 'group', 'install']

SHOULD_ALPHABETIZE = ['COMPONENTS', 'DEPENDENCIES', 'FILES', 'CATKIN_DEPENDS']

def get_ordering_index(cmd):
    for i, o in enumerate(ORDERING):
        if type(o)==list:
            if cmd in o:
                return i
        elif cmd==o:
            return i
    if cmd:        
        print '\tUnsure of ordering for', cmd        
    return len(ORDERING)                

class Section:
    def __init__(self, name='', values=None, pre='', tab=None):
        self.name = name
        if values is None:
            self.values = []
        else:    
            self.values = values
        self.pre = pre
        self.tab = tab
        
    def add(self, v):
        self.values.append(v)
        
    def remove_pattern(self, pattern):
        self.values = [v for v in self.values if pattern not in v]
        
    def is_valid(self):
        return len(self.name)>0 or len(self.values)>0    
        
    def __repr__(self):
        if CFG.should('alphabetize_cmake_options') and self.name in SHOULD_ALPHABETIZE:
            self.values = sorted(self.values)
    
        s = self.pre
        if len(self.name)>0:
            s += self.name
            if self.tab is None and len(self.values)>0:
                s += ' '
            elif len(self.values)>0:
                s += '\n' + ' ' *self.tab
        if self.tab is None:
            s += ' '.join(self.values)
        else:
            s += ('\n' + ' '*self.tab).join(self.values)
        return s

class Command:
    def __init__(self, cmd):
        self.cmd = cmd
        self.inline_count = -1
        self.tab = 0

        self.sections = []
            
    def get_section(self, key):
        for s in self.sections:
            if s.name==key:
                return s
        return None

    def add_section(self, key, values=[]):
        self.sections.append(Section(key, values))
        
    def add(self, section):
        if section:
            self.sections.append(section)
            
    def first_token(self):
        return self.sections[0].values[0]
        
    def __repr__(self):
        s = self.cmd + '('
        s += ' '.join(map(str,self.sections))
        if '\n' in s:
            s += '\n'
        s += ')'
        return s

from roscompile.cmake_parser import scanner, c_scanner

class CMake:
    def __init__(self, fn, name=None):
        self.fn = fn
        self.name = name        
        self.contents = scanner.parse(fn)
        self.content_map = defaultdict(list)
        for c in self.contents:
            if type(c)==str:
                continue
            self.content_map[ c.cmd ].append(c) 

    def section_check(self, items, cmd_name, section_name):        
        if len(items)==0:
            return
            
        if cmd_name not in self.content_map:
            params = section_name + ' '  + ' '.join(items)
            self.add_command('%s(%s)'%(cmd_name,params))
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
        self.section_check(pkgs, 'catkin_package', 'CATKIN_DEPENDS')
        
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

    def add_command(self, s):
        cmd = c_scanner.parse(s)
        self.contents.append(cmd)
        self.content_map[cmd.cmd].append(cmd)
        
    def check_exported_dependencies(self):
        targets = []
        for cmd in self.content_map['add_library'] + self.content_map['add_executable']:
            targets.append(cmd.first_token())
            
        for cmd in self.content_map['add_dependencies']:
            target = cmd.first_token()
            if target in targets:
                targets.remove(target)
                cmd.sections[0].remove_pattern('_generate_messages_cpp')
                cmd.sections[0].remove_pattern('_gencpp')
                cmd.sections[0].add('${catkin_EXPORTED_TARGETS}')
        for target in targets:
            self.add_command('add_dependencies(%s ${catkin_EXPORTED_TARGETS})'%target)

    def enforce_ordering(self):
        chunks = []
        current = []
        group = None
        for x in self.contents:
            current.append(x)
            if x.__class__==Command:
                if x.cmd == 'if':
                    group = 'endif'
                elif x.cmd == 'foreach':
                    group = 'endforeach'
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

    def output(self, fn=None):
        if CFG.should('enforce_cmake_ordering'):
            self.enforce_ordering()
        
        s = str(self)
        
        if CFG.should('remove_dumb_cmake_comments'):    
            D = {'package': self.name}
            for line in IGNORE_LINES:
                s = s.replace(line, '')
            for pattern in IGNORE_PATTERNS:
                s = s.replace(pattern % D, '')    
        if CFG.should('remove_empty_cmake_lines'):        
            while '\n\n\n' in s:    
                s = s.replace('\n\n\n', '\n\n')    
        
        if fn is None:
            fn = self.fn
        with open(fn, 'w') as cmake:
            cmake.write(s)

