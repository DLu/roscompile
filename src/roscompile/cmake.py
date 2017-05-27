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
            self.values = values
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

    def add_section(self, key, values=[]):
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

    def __repr__(self):
        if self.original and not self.changed:
            return self.original

        s = self.cmd + self.pre_paren + '('
        for section in map(str, self.sections):
            if s[-1] not in '( \n':
                s += ' '
            s += section
        s += ')'
        return s

from roscompile.cmake_parser import parse_file

class CMake:
    def __init__(self, fn, name=None):
        self.fn = fn
        self.name = name
        self.root = os.path.split(fn)[0]
        if os.path.exists(fn):
            self.contents = parse_file(open(fn).read())
        else:
            self.contents = []
        self.content_map = defaultdict(list)
        for c in self.contents:
            if type(c) == str:
                continue
            self.content_map[c.cmd].append(c)

    def section_check(self, items, cmd_name, section_name='', zero_okay=False):
        if len(items) == 0 and not zero_okay:
            return

        if cmd_name not in self.content_map:
            if len(items) > 0:
                params = section_name + ' ' + ' '.join(items)
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

    def check_dependencies(self, pkgs):
        self.section_check(pkgs, 'find_package', 'COMPONENTS')
        self.section_check(pkgs, 'catkin_package', 'CATKIN_DEPENDS')

    def check_generators(self, msgs, srvs, actions, cfgs, deps):
        self.section_check(map(os.path.basename, msgs), 'add_message_files', 'FILES')
        self.section_check(map(os.path.basename, srvs), 'add_service_files', 'FILES')
        self.section_check(map(os.path.basename, actions), 'add_action_files', 'FILES')

        if len(msgs) + len(srvs) + len(actions) > 0:
            self.section_check(['message_generation'], 'find_package', 'COMPONENTS')
            self.section_check(['message_runtime'], 'catkin_package', 'CATKIN_DEPENDS')

            self.section_check(deps, 'generate_messages', 'DEPENDENCIES', zero_okay=True)

        cfgs = ['cfg/' + os.path.basename(cfg) for cfg in cfgs]
        self.section_check(cfgs, 'generate_dynamic_reconfigure_options', '')
        if len(cfgs) > 0:
            self.section_check(['dynamic_reconfigure'], 'find_package', 'COMPONENTS')

    def add_command_string(self, s):
        for cmd in parse_file(s):
            self.add_command(cmd)

    def add_command(self, cmd):
        if len(self.contents) > 0 and type(self.contents[-1]) != str:
            self.contents.append('\n')
        self.contents.append(cmd)
        self.content_map[cmd.cmd].append(cmd)

    def remove_command(self, cmd):
        print '\tRemoving %s' % str(cmd).replace('\n', ' ').replace('  ', '')
        self.contents.remove(cmd)
        self.content_map[cmd.cmd].remove(cmd)

    def get_libraries(self):
        return [cmd.first_token() for cmd in self.content_map['add_library']]

    def get_executables(self):
        return [cmd.first_token() for cmd in self.content_map['add_executable']]

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

    def check_include_path(self):
        self.section_check(['include'], 'catkin_package', 'INCLUDE_DIRS')
        self.section_check(['include'], 'include_directories')

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

        if cmd is None:
            print '\tInstalling ', ', '.join(items)
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
            self.add_command_string('%s(PROGRAMS %s\n' +
                                    '                      DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})'
                                    % (cmd, ' '.join(execs)))
        else:
            self.section_check(execs, cmd, 'PROGRAMS')

    def enforce_ordering(self):
        chunks = []
        current = []
        group = None
        for x in self.contents:
            current.append(x)
            if x.__class__ == Command:
                if x.cmd == 'if':
                    group = 'endif'
                elif x.cmd == 'foreach':
                    group = 'endforeach'
                elif x.cmd == group:
                    chunks.append(('group', current))
                    current = []
                    group = None
                elif group is None:
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
