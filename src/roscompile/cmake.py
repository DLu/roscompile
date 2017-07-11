from collections import defaultdict
import re
import os.path
from roscompile.config import CFG
from roscompile.util import clean_contents, remove_blank_lines, remove_all_hashes

BREAKERS = ['catkin_package']
ALL_CAPS = re.compile('^[A-Z_]+$')

ORDERING = ['cmake_minimum_required', 'project', 'find_package', 'pkg_check_modules', 'catkin_python_setup',
            'add_definitions', 'add_message_files', 'add_service_files', 'add_action_files',
            'generate_dynamic_reconfigure_options', 'generate_messages', 'catkin_package', 'catkin_metapackage',
            ['add_library', 'add_executable', 'target_link_libraries', 'add_dependencies', 'include_directories'],
            ['roslint_cpp', 'roslint_python'],
            'catkin_add_gtest', 'group',
            ['install', 'catkin_install_python']]

SHOULD_ALPHABETIZE = ['COMPONENTS', 'DEPENDENCIES', 'FILES', 'CATKIN_DEPENDS']

INSTALL_CONFIGS = {
    'exec':    ('TARGETS', {'${CATKIN_PACKAGE_BIN_DESTINATION}': 'RUNTIME DESTINATION'}),
    'library': ('TARGETS', {'${CATKIN_PACKAGE_LIB_DESTINATION}': ('ARCHIVE DESTINATION', 'LIBRARY DESTINATION'),
                            '${CATKIN_GLOBAL_BIN_DESTINATION}':  'RUNTIME DESTINATION'}),
    'headers': ('FILES',   {'${CATKIN_PACKAGE_INCLUDE_DESTINATION}': 'DESTINATION'}),
    'misc':    ('FILES',   {'${CATKIN_PACKAGE_SHARE_DESTINATION}':   'DESTINATION'})
}

def get_ordering_index(cmd):
    for i, o in enumerate(ORDERING):
        if type(o) == list:
            if cmd in o:
                return i
        elif cmd == o:
            return i
    if cmd:
        print '\tUnsure of ordering for', cmd
    return len(ORDERING)

def get_install_type(destination):
    for name, (ft, m) in INSTALL_CONFIGS.iteritems():
        if destination in m:
            return name

def make_list(value):
    if type(value) == str:
        return [value]
    else:
        return value

def install_sections(cmd, D, subfolder=''):
    for destination, value in D.iteritems():
        for key in make_list(value):
            if len(subfolder) > 0:
                destination = os.path.join(destination, subfolder)
            cmd.check_complex_section(key, destination)

def get_install_types(cmd, subfolder=''):
    types = set()
    for section in cmd.get_sections('DESTINATION'):
        the_folder = section.values[0]
        if len(subfolder) > 0:
            the_folder = the_folder.replace('/' + subfolder, '')
        type_ = get_install_type(the_folder)
        if type_:
            types.add(type_)
    return types

def remove_install_section(cmd, destination_map):
    empty_sections_to_remove = {}
    for destination, value in destination_map.iteritems():
        for key in make_list(value):
            parts = key.split()
            if len(parts) == 2:
                empty_sections_to_remove[parts[0]] = destination
    sections = cmd.get_real_sections()
    to_remove = []
    for i, section in enumerate(sections):
        if section.name not in empty_sections_to_remove or len(section.values) != 0:
            continue
        next = sections[i + 1]
        dest = empty_sections_to_remove[section.name]
        if next.name == 'DESTINATION' and len(next.values) == 1 and next.values[0] == dest:
            to_remove.append(section)
            to_remove.append(next)
    if len(to_remove) > 0:
        for section in to_remove:
            cmd.sections.remove(section)
        cmd.changed = True

class SectionStyle:
    def __init__(self):
        self.prename = ''
        self.name_val_sep = ' '
        self.val_sep = ' '

    def __repr__(self):
        return 'SectionStyle(%s, %s, %s)' % (repr(self.prename), repr(self.name_val_sep), repr(self.val_sep))

class Section:
    def __init__(self, name='', values=None, style=SectionStyle()):
        self.name = name
        if values is None:
            self.values = []
        else:
            self.values = list(values)
        self.style = style

    def add(self, v):
        self.values.append(v)

    def remove_pattern(self, pattern):
        self.values = [v for v in self.values if pattern not in v]

    def is_valid(self):
        return len(self.name) > 0 or len(self.values) > 0

    def __repr__(self):
        if CFG.should('alphabetize') and self.name in SHOULD_ALPHABETIZE:
            self.values = sorted(self.values)

        s = self.style.prename
        if len(self.name) > 0:
            s += self.name
            s += self.style.name_val_sep
        s += self.style.val_sep.join(self.values)
        return s

class Command:
    def __init__(self, cmd):
        self.cmd = cmd
        self.original = None
        self.changed = False
        self.pre_paren = ''

        self.inline_count = -1

        self.sections = []

    def get_real_sections(self):
        return [s for s in self.sections if type(s) != str]

    def get_section(self, key):
        for s in self.get_real_sections():
            if s.name == key:
                return s
        return None

    def get_sections(self, key):
        return [s for s in self.get_real_sections() if s.name == key]

    def add_section(self, key, values=None):
        self.sections.append(Section(key, values))
        self.changed = True

    def add(self, section):
        if section:
            self.sections.append(section)
            self.changed = True

    def check_complex_section(self, key, value):
        words = key.split()
        if len(words) == 1:
            section = self.get_section(key)
        else:
            i = 0
            section = None
            for section_i in self.get_real_sections():
                if section_i.name == words[i]:
                    if i < len(words) - 1:
                        i += 1
                    else:
                        section = section_i
                        break
                else:
                    i = 0

        if section:
            if value not in section.values:
                section.add(value)
                self.changed = True
        else:
            self.add_section(key, [value])

    def first_token(self):
        return self.get_real_sections()[0].values[0]

    def get_tokens(self):
        tokens = []
        for section in self.get_real_sections():
            tokens += section.values
        return tokens

    def add_token(self, s):
        sections = self.get_real_sections()
        if len(sections) == 0:
            self.add(Section(values=[s]))
        else:
            last = sections[-1]
            last.values.append(s)
        self.changed = True

    def __repr__(self):
        if self.original and not self.changed:
            return self.original

        s = self.cmd + self.pre_paren + '('
        for section in map(str, self.sections):
            if s[-1] not in '( \n' and section[0] not in ' \n':
                s += ' '
            s += section
        if '\n' in s and s[-1] != '\n':
            s += '\n'
        s += ')'
        return s

class CommandGroup:
    def __init__(self, initial_tag, sub, close_tag):
        self.initial_tag = initial_tag
        self.sub = sub
        self.close_tag = close_tag

    def __repr__(self):
        return str(self.initial_tag) + str(self.sub) + str(self.close_tag)

from roscompile.cmake_parser import parse_file, parse_command

class CMake:
    def __init__(self, fn=None, name=None, initial_contents=None, indent=0):
        self.fn = fn
        self.name = name
        self.contents = []
        self.root = None
        self.content_map = defaultdict(list)
        self.indent = indent

        if initial_contents:
            contents = initial_contents
        elif fn is not None and os.path.exists(fn):
            contents = parse_file(open(fn).read())
            self.root = os.path.split(fn)[0]
        else:
            contents = []

        current = []
        group = None
        depth = 0

        for x in contents:
            if group is None:
                if x.__class__ == Command and x.cmd in ['if', 'foreach']:
                    group = x
                    depth = 1
                else:
                    self.contents.append(x)
                    if type(x) != str:
                        self.content_map[x.cmd].append(x)
            else:
                if x.__class__ == Command:
                    if x.cmd == group.cmd:
                        depth += 1
                    elif x.cmd == 'end' + group.cmd:
                        depth -= 1
                        if depth == 0:
                            sub = CMake(initial_contents=current, indent=self.indent + 1)
                            cg = CommandGroup(group, sub, x)
                            self.contents.append(cg)
                            self.content_map['group'].append(cg)
                            group = None
                            current = []
                            continue
                current.append(x)
        # Shouldn't happen, but resolve leftovers
        if len(current) > 0:
            sub = CMake(initial_contents=current, indent=self.indent + 1)
            cg = CommandGroup(group, sub, '')
            self.contents.append(cg)
            self.content_map['group'].append(cg)

    def resolve_variables(self, s):
        VARS = {'${PROJECT_NAME}': self.name}
        for k, v in VARS.iteritems():
            s = s.replace(k, v)
        return s

    def section_check(self, items, cmd_name, section_name='', zero_okay=False, prefix=''):
        if len(items) == 0 and not zero_okay:
            return

        if cmd_name not in self.content_map:
            if len(items) > 0:
                params = prefix + section_name + ' ' + ' '.join(items)
                self.add_command_string('%s(%s)' % (cmd_name, params))
                print '\tAdding new %s command to CMakeLists.txt with %s' % (cmd_name, params)
            else:
                self.add_command(Command(cmd_name))
                print '\tAdding new %s command to CMakeLists.txt' % cmd_name
            return

        section = None
        for cmd in self.content_map[cmd_name]:
            s = cmd.get_section(section_name)
            if s:
                if section is None:
                    section = s
                items = [item for item in items if item not in s.values]
                break
        if len(items) == 0:
            return
        if section:
            section.values += items
            cmd.changed = True
        else:
            cmd.add_section(section_name, items)
        print '\tAdding %s to the %s/%s section of your CMakeLists.txt' % (str(items), cmd_name, section_name)

    def check_dependencies(self, pkgs, check_catkin_pkg=True):
        self.section_check(pkgs, 'find_package', 'COMPONENTS', prefix='catkin REQUIRED ')
        if check_catkin_pkg:
            self.section_check(pkgs, 'catkin_package', 'CATKIN_DEPENDS')

    def check_generators(self, msgs, srvs, actions, cfgs, deps):
        self.section_check(map(os.path.basename, msgs), 'add_message_files', 'FILES')
        self.section_check(map(os.path.basename, srvs), 'add_service_files', 'FILES')
        self.section_check(map(os.path.basename, actions), 'add_action_files', 'FILES')

        if len(msgs) + len(srvs) + len(actions) > 0:
            self.section_check(['message_generation'], 'find_package', 'COMPONENTS')
            self.section_check(['message_runtime'], 'catkin_package', 'CATKIN_DEPENDS')
            for cmd in self.content_map['catkin_package']:
                section = cmd.get_section('CATKIN_DEPENDS')
                if 'message_generation' in section.values:
                    section.remove_pattern('message_generation')
                    cmd.changed = True

            self.section_check(deps, 'generate_messages', 'DEPENDENCIES', zero_okay=True)

        cfgs = ['cfg/' + os.path.basename(cfg) for cfg in cfgs]
        self.section_check(cfgs, 'generate_dynamic_reconfigure_options', '')
        if len(cfgs) > 0:
            self.section_check(['dynamic_reconfigure'], 'find_package', 'COMPONENTS')

    def add_command_string(self, s, in_test_section=False):
        for cmd in parse_file(s):
            self.add_command(cmd, in_test_section)

    def add_command(self, cmd, in_test_section=False):
        if in_test_section:
            cg = self.get_test_section(create_if_needed=True)
            cg.add_command(cmd)
        else:
            if len(self.contents) > 0 and type(self.contents[-1]) != str:
                self.contents.append('\n')
            if self.indent > 0:
                self.contents.append('  ' * self.indent)
            self.contents.append(cmd)
            self.content_map[cmd.cmd].append(cmd)
            if self.indent > 0:
                self.contents.append('\n')

    def remove_command(self, cmd):
        print '\tRemoving %s' % str(cmd).replace('\n', ' ').replace('  ', '')
        self.contents.remove(cmd)
        self.content_map[cmd.cmd].remove(cmd)

    def get_libraries(self):
        return [cmd.first_token() for cmd in self.content_map['add_library']]

    def get_executables(self):
        return [cmd.first_token() for cmd in self.content_map['add_executable']]

    def get_source_helper(self, tagname):
        lib_src = set()
        for cmd in self.content_map[tagname]:
            tokens = cmd.get_tokens()
            lib_src.update(tokens[1:])
        return lib_src

    def get_library_source(self):
        return self.get_source_helper('add_library')

    def get_executable_source(self):
        return self.get_source_helper('add_executable')

    def lookup_library(self, src_fn):
        for cmd in self.content_map['add_library']:
            tokens = cmd.get_tokens()
            if src_fn in tokens:
                return self.resolve_variables(tokens[0])

    def get_test_sections(self):
        sections = []
        for content in self.content_map['group']:
            cmd = content.initial_tag
            if cmd.cmd != 'if' or len(cmd.sections) == 0 or cmd.sections[0].name != 'CATKIN_ENABLE_TESTING':
                continue
            sections.append(content.sub)
        return sections

    def get_test_section(self, create_if_needed=False):
        sections = self.get_test_sections()
        if len(sections) > 0:
            return sections[0]
        if not create_if_needed:
            return None
        # Create Test Section
        if len(self.contents) > 0 and type(self.contents[-1]) != str:
            self.contents.append('\n')
        cg = CommandGroup(parse_command('if(CATKIN_ENABLE_TESTING)'),
                          CMake(initial_contents=['\n'], indent=self.indent + 1),
                          parse_command('endif()')
                          )
        self.contents.append(cg)
        self.content_map['group'].append(cg)
        return cg.sub

    def get_test_source(self):
        test_files = set()
        for sub in self.get_test_sections():
            test_files.update(sub.get_library_source())
            test_files.update(sub.get_executable_source())
        return test_files

    def check_exported_dependencies(self, pkg_name, deps):
        if len(deps) == 0:
            return
        if pkg_name in deps:
            self_depend = True
            if len(deps) == 1:
                cat_depend = False
            else:
                cat_depend = True
        else:
            self_depend = False
            cat_depend = True

        marks = []
        if cat_depend:
            marks.append('${catkin_EXPORTED_TARGETS}')
        if self_depend:
            marks.append('${%s_EXPORTED_TARGETS}' % pkg_name)

        targets = self.get_libraries() + self.get_executables()

        for cmd in self.content_map['add_dependencies']:
            target = cmd.first_token()
            if target in targets:
                targets.remove(target)
                cmd.sections[0].remove_pattern('_generate_messages_cpp')
                cmd.sections[0].remove_pattern('_gencpp')
                if cat_depend and '${catkin_EXPORTED_TARGETS}' not in cmd.sections[0].values:
                    cmd.sections[0].add('${catkin_EXPORTED_TARGETS}')
                if self_depend and '${%s_EXPORTED_TARGETS}' % pkg_name not in cmd.sections[0].values:
                    cmd.sections[0].add('${%s_EXPORTED_TARGETS}' % pkg_name)

        for target in targets:
            self.add_command_string('add_dependencies(%s %s)' % (target, ' '.join(marks)))

    def check_libraries(self):
        CATKIN = '${catkin_LIBRARIES}'
        targets = self.get_libraries() + self.get_executables()
        for cmd in self.content_map['target_link_libraries']:
            tokens = cmd.get_tokens()
            if tokens[0] in targets:
                if CATKIN not in tokens:
                    print '\tAdding %s to target_link_libraries for %s' % (CATKIN, tokens[0])
                    cmd.add_token(CATKIN)
                targets.remove(tokens[0])
                continue
        for target in targets:
            print '\tAdding target_link_libraries for %s' % target
            self.add_command_string('target_link_libraries(%s %s)' % (target, CATKIN))

    def check_include_path(self):
        self.section_check(['include'], 'catkin_package', 'INCLUDE_DIRS')
        self.section_check(['include'], 'include_directories')

    def add_catkin_include_path(self):
        self.section_check(['${catkin_INCLUDE_DIRS}'], 'include_directories')

    def check_library_setup(self):
        self.section_check(self.get_libraries(), 'catkin_package', 'LIBRARIES')

    def get_commands_by_type(self, name, subfolder=''):
        matches = []
        for cmd in self.content_map['install']:
            if name in get_install_types(cmd, subfolder):
                matches.append(cmd)
        return matches

    def install_section_check(self, items, install_type, directory=False, subfolder=''):
        section_name, destination_map = INSTALL_CONFIGS[install_type]
        if directory and section_name == 'FILES':
            section_name = 'DIRECTORY'
        cmds = self.get_commands_by_type(install_type, subfolder)
        if len(items) == 0:
            for cmd in cmds:
                if len(get_install_types(cmd)) == 1:
                    self.remove_command(cmd)
                else:
                    remove_install_section(cmd, destination_map)
            return

        cmd = None
        for cmd in cmds:
            install_sections(cmd, destination_map)
            section = cmd.get_section(section_name)
            if not section:
                continue
            section.values = [value for value in section.values if value in items]
            items = [item for item in items if item not in section.values]

        if len(items) == 0:
            return

        print '\tInstalling ', ', '.join(items)
        if cmd is None:
            cmd = Command('install')
            cmd.add_section(section_name, items)
            self.add_command(cmd)
            install_sections(cmd, destination_map, subfolder)
        elif section:
            section = cmd.get_section(section_name)
            section.values += items

    def update_cplusplus_installs(self):
        self.install_section_check(self.get_executables(), 'exec')
        self.install_section_check(self.get_libraries(), 'library')
        if self.name and os.path.exists(os.path.join(self.root, 'include', self.name)):
            self.install_section_check(['include/${PROJECT_NAME}/'], 'headers', True)

    def update_misc_installs(self, items, subfolder=''):
        self.install_section_check(items, 'misc', False, subfolder)

    def update_python_installs(self, execs):
        if len(execs) == 0:
            return
        cmd = 'catkin_install_python'
        if cmd not in self.content_map:
            self.add_command_string('%s(PROGRAMS %s\n'
                                    '                      DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})'
                                    % (cmd, ' '.join(execs)))
        else:
            self.section_check(execs, cmd, 'PROGRAMS')

    def catkin_package_cleanup(self):
        for cmd in self.content_map['catkin_package']:
            for section in cmd.get_real_sections():
                section.style.prename = '\n    '
            cmd.changed = True

    def msg_srv_cleanup(self):
        for cmd in self.content_map['add_message_files'] + self.content_map['add_service_files']:
            for section in cmd.get_real_sections():
                if len(section.values) > 1:
                    section.style.name_val_sep = '\n    '
                    section.style.val_sep = '\n    '
                cmd.changed = True

    def enforce_ordering(self):
        chunks = []
        current = []
        for x in self.contents:
            current.append(x)
            if x.__class__ == CommandGroup:
                chunks.append(('group', current))
                current = []
            elif x.__class__ == Command:
                chunks.append((x.cmd, current))
                current = []
        if len(current) > 0:
            chunks.append((None, current))

        self.contents = []

        for a, b in sorted(chunks, key=lambda d: get_ordering_index(d[0])):
            self.contents += b

    def __repr__(self):
        return ''.join(map(str, self.contents))

    def output(self, fn=None):
        if CFG.should('enforce_cmake_ordering'):
            self.enforce_ordering()

        s = str(self)
        if CFG.should('remove_dumb_cmake_comments'):
            s = remove_all_hashes(s)
            s = clean_contents(s, 'cmake', {'package': self.name})
        if CFG.should('remove_empty_cmake_lines'):
            s = remove_blank_lines(s)
        if '(\n)' in s:
            s = s.replace('(\n)', '()')

        if fn is None:
            fn = self.fn
        with open(fn, 'w') as cmake:
            cmake.write(s)
