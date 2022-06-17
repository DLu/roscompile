import collections
import re

VARIABLE_PATTERN = re.compile(r'\$\{([^\}]+)\}')
QUOTED_PATTERN = re.compile(r'"([^"]+)"')

BUILD_TARGET_COMMANDS = ['add_library', 'add_executable', 'add_rostest',
                         'target_include_directories', 'add_dependencies', 'target_link_libraries',
                         'set_target_properties', 'ament_target_dependencies']
TEST_COMMANDS = [('group', 'CATKIN_ENABLE_TESTING'), 'catkin_download_test_data',
                 'roslint_cpp', 'roslint_python', 'roslint_add_test',
                 'catkin_add_nosetests', 'catkin_add_gtest', 'add_rostest_gtest']
INSTALL_COMMANDS = ['install', 'catkin_install_python']

BASE_ORDERING = ['cmake_minimum_required', 'project', 'set_directory_properties', 'find_package', 'pkg_check_modules',
                 'set', 'catkin_generate_virtualenv', 'catkin_python_setup', 'add_definitions',
                 'add_message_files', 'add_service_files', 'add_action_files', 'rosidl_generate_interfaces',
                 'generate_dynamic_reconfigure_options', 'generate_messages', 'catkin_package', 'catkin_metapackage',
                 BUILD_TARGET_COMMANDS + ['include_directories'],
                 'ament_target_dependencies', 'ament_export_include_directories', 'ament_export_libraries',
                 'ament_export_dependencies',
                 'ament_package']


def get_style(cmake):
    """Examine the contents of the cmake parameter and determine the style.

    There are four possible styles:
    1) test_first (where test commands come strictly before install commands)
    2) install_first (where test commands come strictly after install commands)
    3) mixed (where test and install commands are not clearly delineated)
    4) None (where there are only install commands, or only test commands, or neither)
    """
    cats = []
    for content in cmake.contents:
        cat = None
        if isinstance(content, CommandGroup) and is_testing_group(content):
            cat = 'test'
        elif isinstance(content, Command):
            if content.command_name in TEST_COMMANDS:
                cat = 'test'
            elif content.command_name in INSTALL_COMMANDS:
                cat = 'install'
        if cat is None:
            continue

        if len(cats) == 0 or cats[-1] != cat:
            cats.append(cat)

        if len(cats) > 2:
            return 'mixed'
    if len(cats) < 2:
        return None
    first_cat = cats[0]
    return first_cat + '_first'


def get_ordering(style):
    """Given the style, return the correct ordering."""
    if style == 'install_first':
        return BASE_ORDERING + INSTALL_COMMANDS + TEST_COMMANDS
    else:
        return BASE_ORDERING + TEST_COMMANDS + INSTALL_COMMANDS


def get_ordering_index(command_name, ordering):
    """
    Given a command name, determine the integer index into the ordering.

    The ordering is a list of strings and arrays of strings.

    If the command name matches one of the strings in the inner arrays,
    the index of the inner array is returned.

    If the command name matches one of the other strings, its index is returned.

     Otherwise, the length of the ordering is returned (putting non-matches at the end)
    """
    for i, o in enumerate(ordering):
        if type(o) == list:
            if command_name in o:
                return i
        elif command_name == o:
            return i
    if command_name:
        print('\tUnsure of ordering for ' + str(command_name))
    return len(ordering)


def get_sort_key(content, anchors, ordering):
    """
    Given a piece of cmake content, return a tuple representing its sort_key.

    The first element of the tuple is the ordering_index of the content.
    The second element is an additional variable used for sorting among elements with the same ordering_index

    Most notably, we want all build commands with a particular library/executable to be grouped together.
    In that case, we use the anchors parameter, which is an ordered list of all the library/executables in the file.
    Then, the second variable is a tuple itself, with the first element being the index of library/executable in the
    anchors list, and the second is an integer representing the canonical order of the build commands.
    """
    if content is None:
        return len(ordering) + 1, None
    index = None
    key = ()
    if content.__class__ == CommandGroup:
        key_token = ()
        for token in content.initial_tag.get_tokens(include_name=True):
            if token == 'NOT':
                continue
            key_token = token
            break
        index = get_ordering_index(('group', key_token), ordering)
    else:  # Command
        index = get_ordering_index(content.command_name, ordering)
        if content.command_name in BUILD_TARGET_COMMANDS:
            token = content.first_token()
            if token not in anchors:
                anchors.append(token)
            key = anchors.index(token), BUILD_TARGET_COMMANDS.index(content.command_name)
        elif content.command_name == 'include_directories' and 'include_directories' in anchors:
            key = -1, anchors.index('include_directories')
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

    def add_values(self, new_values, alpha_order=True):
        """Add the new_values to the values.

        If alpha_order is true AND the existing values are already alphabetized,
        add the new values in alphabetical order.
        """
        # Check if existing values are sorted
        if alpha_order and self.values == sorted(self.values):
            all_values = self.values + list(new_values)
            self.values = sorted(all_values)
        else:
            self.values += sorted(new_values)

    def is_valid(self):
        return len(self.name) > 0 or len(self.values) > 0

    def __repr__(self):
        s = self.style.prename
        if len(self.name) > 0:
            s += self.name
            if len(self.values) > 0 or '\n' in self.style.name_val_sep:
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


def is_testing_group(content):
    cmd = content.initial_tag
    return cmd.command_name == 'if' and cmd.sections and cmd.sections[0].name == 'CATKIN_ENABLE_TESTING'


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

        self.existing_style = get_style(self)

    def get_project_name(self):
        project_tags = self.content_map['project']
        if not project_tags:
            return ''
        # Get all tokens just in case the name is all caps
        return project_tags[0].get_tokens(include_name=True)[0]

    def resolve_variables(self, var):
        if type(var) == str:
            s = var
            m = VARIABLE_PATTERN.search(s)
            if not m:
                return s

            for k, v in self.variables.items():
                s = s.replace('${%s}' % k, v)
            return s
        else:
            tokens = []
            for token in var:
                if token and token[0] == '#':
                    continue
                m = QUOTED_PATTERN.match(token)
                if m:
                    token = m.group(1)
                token = self.resolve_variables(token)
                tokens += token.split(' ')
            return tokens

    def get_resolved_tokens(self, cmd, include_name=False):
        return self.resolve_variables(cmd.get_tokens(include_name))

    def get_insertion_index(self, cmd):
        anchors = self.get_ordered_build_targets()
        ordering = get_ordering(self.get_desired_style())

        new_key = get_sort_key(cmd, anchors, ordering)
        i_index = 0

        for i, content in enumerate(self.contents):
            if type(content) == str:
                continue
            key = get_sort_key(content, anchors, ordering)
            if key <= new_key:
                i_index = i + 1
            elif key[0] != len(ordering):
                return i_index
        return len(self.contents)

    def add_command(self, cmd):
        i_index = self.get_insertion_index(cmd)
        sub_contents = []
        if i_index > 0 and type(self.contents[i_index - 1]) != str:
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
        print('\tRemoving %s' % str(cmd).replace('\n', ' ').replace('  ', ''))
        self.contents.remove(cmd)
        self.content_map[cmd.command_name].remove(cmd)

    def remove_all_commands(self, cmd_name):
        cmds = list(self.content_map[cmd_name])
        for cmd in cmds:
            self.remove_command(cmd)

    def is_metapackage(self):
        return len(self.content_map['catkin_metapackage']) > 0

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
        for deps in self.get_source_build_rules(tag).values():
            lib_src.update(deps)
        return lib_src

    def get_library_source(self):
        return self.get_source_helper('add_library')

    def get_executable_source(self):
        return self.get_source_helper('add_executable')

    def get_libraries(self):
        return list(self.get_source_build_rules('add_library').keys())

    def get_executables(self):
        return list(self.get_source_build_rules('add_executable').keys())

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
            if is_testing_group(content):
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
        """Return the first command that matches the command name and has a matching section name.

        If the section name is not found, return a command with the matching command name
        """
        if len(self.content_map[command_name]) == 0:
            return None, None
        for cmd in self.content_map[command_name]:
            s = cmd.get_section(section_name)
            if s:
                return cmd, s
        return self.content_map[command_name][0], None

    def section_check(self, items, cmd_name, section_name='', zero_okay=False, alpha_order=True):
        """Ensure there's a CMake command of the given type with the given section name and items."""
        if len(items) == 0 and not zero_okay:
            return

        cmd, section = self.get_command_section(cmd_name, section_name)

        if cmd is None:
            cmd = Command(cmd_name)
            self.add_command(cmd)

        if section is None:
            cmd.add_section(section_name, sorted(items))
        else:
            existing = self.resolve_variables(section.values)
            needed_items = [item for item in items if item not in existing and item not in section.values]
            if needed_items:
                section.add_values(needed_items, alpha_order)
                cmd.changed = True

    def get_clusters(self, desired_style):
        """Return a list of clusters where each cluster is an array of strings with a Command/CommandGroup at the end.

        The clusters are sorted according to the desired style.
        The strings are grouped at the beginning to maintain the newlines and indenting before each Command.
        """
        anchors = self.get_ordered_build_targets()
        ordering = get_ordering(desired_style)
        clusters = []
        current = []
        for content in self.contents:
            current.append(content)
            if type(content) == str:
                continue
            key = get_sort_key(content, anchors, ordering)
            clusters.append((key, current))
            current = []
        if len(current) > 0:
            clusters.append((get_sort_key(None, anchors, ordering), current))

        return [kv[1] for kv in sorted(clusters, key=lambda kv: kv[0])]

    def get_desired_style(self, default_style=None):
        """Determine which style to use, install_first or test_first.

        If the default style is one of those two, use it
        """
        if default_style in ['install_first', 'test_first']:
            desired_style = default_style
        elif default_style is not None:
            raise RuntimeError('Configured default cmake style "{}"'
                               ' is not install_first or test_first'.format(default_style))
        elif self.existing_style in ['install_first', 'test_first']:
            desired_style = self.existing_style
        else:
            # Otherwise, do test first
            desired_style = 'test_first'

        return desired_style

    def enforce_ordering(self, default_style=None):
        desired_style = self.get_desired_style(default_style)
        clusters = self.get_clusters(desired_style)
        self.contents = []
        for contents in clusters:
            self.contents += contents

        for group in self.content_map['group']:
            group.sub.enforce_ordering(default_style)

    def upgrade_minimum_version(self, new_version):
        """Upgrade the CMake version to the new version (specified as a tuple)."""
        for cmd in self.content_map['cmake_minimum_required']:
            section = cmd.get_section('VERSION')
            version = tuple(map(int, section.values[0].split('.')))
            if version < new_version:
                section.values[0] = '.'.join(map(str, new_version))
                cmd.changed = True

    def __repr__(self):
        return ''.join(map(str, self.contents))

    def write(self, fn=None):
        if fn is None:
            fn = self.file_path
        with open(fn, 'w') as cmake:
            cmake.write(str(self))
