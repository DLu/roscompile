import collections
import re

VARIABLE_PATTERN = re.compile(r'\$\{([^\}]+)\}')
QUOTED_PATTERN = re.compile(r'"([^"]+)"')

BUILD_TARGET_COMMANDS = ['add_library', 'add_executable', 'add_rostest', 'add_dependencies', 'target_link_libraries']

ORDERING = ['cmake_minimum_required', 'project', 'set_directory_properties', 'find_package', 'pkg_check_modules',
            'set', 'catkin_generate_virtualenv', 'catkin_python_setup', 'add_definitions',
            'add_message_files', 'add_service_files', 'add_action_files',
            'generate_dynamic_reconfigure_options', 'generate_messages', 'catkin_package', 'catkin_metapackage',
            BUILD_TARGET_COMMANDS + ['include_directories'],
            ['catkin_download_test_data', 'roslint_cpp', 'roslint_python', 'roslint_add_test', 'catkin_add_nosetests'],
            'catkin_add_gtest', 'group',
            ['install', 'catkin_install_python']]


def get_ordering_index(command_name):
    for i, o in enumerate(ORDERING):
        if type(o) == list:
            if command_name in o:
                return i
        elif command_name == o:
            return i
    if command_name:
        print '\tUnsure of ordering for', command_name
    return len(ORDERING)


def get_sort_key(content, anchors):
    if content is None:
        return len(ORDERING) + 1, None
    index = None
    key = None
    if content.__class__ == CommandGroup:
        index = get_ordering_index('group')
        sections = content.initial_tag.get_real_sections()
        if len(sections) > 0:
            key = sections[0].name
    else:  # Command
        index = get_ordering_index(content.command_name)
        if content.command_name in BUILD_TARGET_COMMANDS:
            token = content.first_token()
            if token not in anchors:
                anchors.append(token)
            key = anchors.index(token), BUILD_TARGET_COMMANDS.index(content.command_name)
        elif content.command_name == 'include_directories' and 'include_directories' in anchors:
            key = anchors.index('include_directories')
    return index, key


class SectionStyle:
    def __init__(self, prename='', name_val_sep=' ', val_sep=' '):
        self.prename = prename
        self.name_val_sep = name_val_sep
        self.val_sep = val_sep

    def __repr__(self):
        return 'SectionStyle(%s, %s, %s)' % (repr(self.prename), repr(self.name_val_sep), repr(self.val_sep))


class Section:
    def __init__(self, name='', values=None, style=None):
        self.name = name
        if values is None:
            self.values = []
        else:
            self.values = list(values)
        if style:
            self.style = style
        else:
            self.style = SectionStyle()

    def add(self, v):
        self.values.append(v)

    def is_valid(self):
        return len(self.name) > 0 or len(self.values) > 0

    def __repr__(self):
        s = self.style.prename
        if len(self.name) > 0:
            s += self.name
            if len(self.values) > 0:
                s += self.style.name_val_sep
        s += self.style.val_sep.join(self.values)
        return s


class Command:
    def __init__(self, command_name):
        self.command_name = command_name
        self.original = None
        self.changed = False
        self.pre_paren = ''
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

    def add_section(self, key, values=None, style=None):
        self.sections.append(Section(key, values, style))
        self.changed = True

    def add(self, section):
        if section:
            self.sections.append(section)
            self.changed = True

    def first_token(self):
        return self.get_real_sections()[0].values[0]

    def remove_sections(self, key):
        bad_sections = self.get_sections(key)
        if not bad_sections:
            return
        self.changed = True
        self.sections = [section for section in self.sections if section not in bad_sections]
        if len(self.sections) == 1 and type(self.sections[0]) == str:
            self.sections = []

    def get_tokens(self, include_name=False):
        tokens = []
        for section in self.get_real_sections():
            if include_name and section.name:
                tokens.append(section.name)
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

        s = self.command_name + self.pre_paren + '('
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


class CMake:
    def __init__(self, file_path=None, initial_contents=None, depth=0):
        self.file_path = file_path
        if initial_contents is None:
            self.contents = []
        else:
            self.contents = initial_contents
        self.content_map = collections.defaultdict(list)
        for content in self.contents:
            if content.__class__ == Command:
                self.content_map[content.command_name].append(content)
            elif content.__class__ == CommandGroup:
                self.content_map['group'].append(content)
        self.depth = depth

        self.variables = {}
        for cmd in self.content_map['set']:
            tokens = cmd.get_tokens(include_name=True)
            self.variables[tokens[0]] = ' '.join(tokens[1:])
        self.variables['PROJECT_NAME'] = self.get_project_name()

    def get_project_name(self):
        project_tags = self.content_map['project']
        if not project_tags:
            return ''
        # Get all tokens just in case the name is all caps
        return project_tags[0].get_tokens(include_name=True)[0]

    def resolve_variables(self, s):
        m = VARIABLE_PATTERN.search(s)
        if not m:
            return s

        for k, v in self.variables.iteritems():
            s = s.replace('${%s}' % k, v)
        return s

    def get_resolved_tokens(self, cmd, include_name=False):
        tokens = []
        for token in cmd.get_tokens(include_name):
            if token and token[0] == '#':
                continue
            m = QUOTED_PATTERN.match(token)
            if m:
                token = m.group(1)
            token = self.resolve_variables(token)
            tokens += token.split(' ')
        return tokens

    def get_insertion_index(self, cmd):
        anchors = self.get_ordered_build_targets()

        new_key = get_sort_key(cmd, anchors)
        i_index = 0

        for i, content in enumerate(self.contents):
            if type(content) == str:
                continue
            key = get_sort_key(content, anchors)
            if key <= new_key:
                i_index = i + 1
            elif key[0] != len(ORDERING):
                return i_index
        return len(self.contents)

    def add_command(self, cmd):
        i_index = self.get_insertion_index(cmd)
        sub_contents = []
        if i_index > 0 and type(self.contents[i_index-1]) != str:
            sub_contents.append('\n')
        if self.depth > 0:
            sub_contents.append('  ' * self.depth)
            sub_contents.append(cmd)
            sub_contents.append('\n')
        else:
            sub_contents.append(cmd)
        if i_index == len(self.contents):
            sub_contents.append('\n')

        self.contents = self.contents[:i_index] + sub_contents + self.contents[i_index:]

        if cmd.__class__ == Command:
            self.content_map[cmd.command_name].append(cmd)
        elif cmd.__class__ == CommandGroup:
            self.content_map['group'].append(cmd)

    def remove_command(self, cmd):
        print '\tRemoving %s' % str(cmd).replace('\n', ' ').replace('  ', '')
        self.contents.remove(cmd)
        self.content_map[cmd.command_name].remove(cmd)

    def remove_all_commands(self, cmd_name):
        cmds = list(self.content_map[cmd_name])
        for cmd in cmds:
            self.remove_command(cmd)

    def get_source_build_rules(self, tag, resolve_target_name=False):
        rules = {}
        for cmd in self.content_map[tag]:
            resolved_tokens = self.get_resolved_tokens(cmd, True)

            if resolve_target_name:
                target = resolved_tokens[0]
            else:
                tokens = cmd.get_tokens(True)
                target = tokens[0]

            deps = resolved_tokens[1:]
            rules[target] = deps
        return rules

    def get_source_helper(self, tag):
        lib_src = set()
        for target, deps in self.get_source_build_rules(tag).iteritems():
            lib_src.update(deps)
        return lib_src

    def get_library_source(self):
        return self.get_source_helper('add_library')

    def get_executable_source(self):
        return self.get_source_helper('add_executable')

    def get_libraries(self):
        return self.get_source_build_rules('add_library').keys()

    def get_executables(self):
        return self.get_source_build_rules('add_executable').keys()

    def get_target_build_rules(self):
        targets = {}
        targets.update(self.get_source_build_rules('add_library'))
        targets.update(self.get_source_build_rules('add_executable'))
        return targets

    def get_ordered_build_targets(self):
        targets = []
        for content in self.contents:
            if content.__class__ != Command:
                continue
            if content.command_name == 'include_directories':
                targets.append('include_directories')
                continue
            elif content.command_name not in BUILD_TARGET_COMMANDS:
                continue
            token = content.first_token()
            if token not in targets:
                targets.append(token)
        return targets

    def get_test_sections(self):
        sections = []
        for content in self.content_map['group']:
            cmd = content.initial_tag
            if cmd.command_name != 'if' or len(cmd.sections) == 0 or cmd.sections[0].name != 'CATKIN_ENABLE_TESTING':
                continue
            sections.append(content.sub)
        return sections

    def get_test_source(self):
        test_files = set()
        for sub in self.get_test_sections():
            test_files.update(sub.get_library_source())
            test_files.update(sub.get_executable_source())
        return test_files

    def get_test_section(self, create_if_needed=False):
        sections = self.get_test_sections()
        if len(sections) > 0:
            return sections[0]
        if not create_if_needed:
            return None

        # Create Test Section
        initial_cmd = Command('if')
        initial_cmd.add_section('CATKIN_ENABLE_TESTING')

        test_contents = CMake(initial_contents=['\n'], depth=self.depth + 1)

        final_cmd = Command('endif')

        cg = CommandGroup(initial_cmd, test_contents, final_cmd)
        self.add_command(cg)
        return cg.sub

    def get_command_section(self, command_name, section_name):
        """ Return the first command that matches the command name and
            has a matching section name. If the section name is not found,
            return a command with the matching command name"""
        if len(self.content_map[command_name]) == 0:
            return None, None
        for cmd in self.content_map[command_name]:
            s = cmd.get_section(section_name)
            if s:
                return cmd, s
        return self.content_map[command_name][0], None

    def section_check(self, items, cmd_name, section_name='', zero_okay=False):
        """ This function ensures that there's a CMake command of the given type
            with the given section name and items somewhere in the file. """
        if len(items) == 0 and not zero_okay:
            return

        cmd, section = self.get_command_section(cmd_name, section_name)

        if cmd is None:
            cmd = Command(cmd_name)
            self.add_command(cmd)

        if section is None:
            cmd.add_section(section_name, sorted(items))
        else:
            needed_items = [item for item in items if item not in section.values]
            section.values += sorted(needed_items)
            cmd.changed = True

    def __repr__(self):
        return ''.join(map(str, self.contents))

    def write(self, fn=None):
        if fn is None:
            fn = self.file_path
        with open(fn, 'w') as cmake:
            cmake.write(str(self))
