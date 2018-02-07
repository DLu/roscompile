from ros_introspection.cmake import Command, CommandGroup, get_sort_key
from ros_introspection.source_code_file import CPLUS
from ros_introspection.resource_list import is_message, is_service
from util import get_ignore_data, roscompile

SHOULD_ALPHABETIZE = ['COMPONENTS', 'DEPENDENCIES', 'FILES', 'CATKIN_DEPENDS']


def check_cmake_dependencies_helper(cmake, dependencies, check_catkin_pkg=True):
    if len(dependencies) == 0:
        return
    if len(cmake.content_map['find_package']) == 0:
        cmd = Command('find_package')
        cmd.add_section('', ['catkin'])
        cmd.add_section('REQUIRED')
        cmake.add_command(cmd)

    for cmd in cmake.content_map['find_package']:
        if cmd.get_tokens()[0] == 'catkin' and cmd.get_section('REQUIRED'):
            section = cmd.get_section('COMPONENTS')
            if section is None:
                cmd.add_section('COMPONENTS', sorted(dependencies))
            else:
                needed_items = dependencies - set(section.values)
                if len(needed_items) > 0:
                    section.values += list(sorted(needed_items))
                    cmd.changed = True
    if check_catkin_pkg:
        cmake.section_check(dependencies, 'catkin_package', 'CATKIN_DEPENDS')


@roscompile
def check_cmake_dependencies(package):
    dependencies = package.get_dependencies_from_msgs()
    dependencies.update(package.get_build_dependencies())
    check_cmake_dependencies_helper(package.cmake, dependencies)


def get_matching_add_depends(cmake, search_target):
    for cmd in cmake.content_map['add_dependencies']:
        target = cmd.first_token()
        if target == search_target:
            return cmd


def match_generator_name(package, name):
    for gen in package.get_all_generators():
        if name == gen.base_name:
            return gen


def get_msg_dependencies_from_source(package, sources):
    deps = set()
    for rel_fn in sources:
        src = package.source_code.sources[rel_fn]
        for pkg, name in src.search_lines_for_pattern(CPLUS):
            if len(name) == 0 or name[-2:] != '.h':
                continue
            name = name.replace('.h', '')
            if is_message(pkg, name) or is_service(pkg, name):
                deps.add(pkg)
            elif pkg == package.name and match_generator_name(package, name):
                deps.add(pkg)
    if package.dynamic_reconfigs:
        deps.add(package.name)
    return sorted(list(deps))


@roscompile
def check_exported_dependencies(package):
    targets = package.cmake.get_target_build_rules()
    for target, sources in targets.iteritems():
        deps = get_msg_dependencies_from_source(package, sources)
        if len(deps) == 0:
            continue

        if package.name in deps:
            self_depend = True
            if len(deps) == 1:
                cat_depend = False
            else:
                cat_depend = True
        else:
            self_depend = False
            cat_depend = True

        add_deps = get_matching_add_depends(package.cmake, target)
        add_add_deps = False

        if add_deps is None:
            add_deps = Command('add_dependencies')
            add_add_deps = True  # Need to wait to add the command for proper sorting

        if len(add_deps.sections) == 0:
            add_deps.add_section('', [target])
            add_deps.changed = True

        section = add_deps.sections[0]
        if cat_depend and '${catkin_EXPORTED_TARGETS}' not in section.values:
            section.add('${catkin_EXPORTED_TARGETS}')
            add_deps.changed = True
        if self_depend:
            tokens = [package.cmake.resolve_variables(s) for s in section.values]
            key = '${%s_EXPORTED_TARGETS}' % package.name
            if key not in tokens:
                section.add(key)
                add_deps.changed = True

        if add_add_deps:
            package.cmake.add_command(add_deps)


def remove_pattern(section, pattern):
    prev_len = len(section.values)
    section.values = [v for v in section.values if pattern not in v]
    return prev_len != len(section.values)


@roscompile
def remove_old_style_cpp_dependencies(package):
    global_changed = False
    targets = package.cmake.get_target_build_rules()
    for target, sources in targets.iteritems():
        add_deps = get_matching_add_depends(package.cmake, target)
        if add_deps is None or len(add_deps.sections) == 0:
            continue

        section = add_deps.sections[0]
        changed = remove_pattern(section, '_generate_messages_cpp')
        changed = remove_pattern(section, '_gencpp') or changed
        changed = remove_pattern(section, '_gencfg') or changed
        if changed:
            add_deps.changed = True
            global_changed = True
    if global_changed:
        check_exported_dependencies(package)


@roscompile
def target_catkin_libraries(package):
    CATKIN = '${catkin_LIBRARIES}'
    targets = package.cmake.get_libraries() + package.cmake.get_executables()
    for cmd in package.cmake.content_map['target_link_libraries']:
        tokens = cmd.get_tokens()
        if tokens[0] in targets:
            if CATKIN not in tokens:
                print '\tAdding %s to target_link_libraries for %s' % (CATKIN, tokens[0])
                cmd.add_token(CATKIN)
            targets.remove(tokens[0])
            continue
    for target in targets:
        print '\tAdding target_link_libraries for %s' % target
        cmd = Command('target_link_libraries')
        cmd.add_section('', [target, CATKIN])
        package.cmake.add_command(cmd)


@roscompile
def check_generators(package):
    if len(package.generators) == 0:
        return

    for gen_type, cmake_cmd in [('msg', 'add_message_files'),
                                ('srv', 'add_service_files'),
                                ('action', 'add_action_files')]:
        names = [gen.name for gen in package.generators[gen_type]]
        package.cmake.section_check(names, cmake_cmd, 'FILES')

    package.cmake.section_check(['message_generation'], 'find_package', 'COMPONENTS')
    package.cmake.section_check(['message_runtime'], 'catkin_package', 'CATKIN_DEPENDS')
    for cmd in package.cmake.content_map['catkin_package']:
        section = cmd.get_section('CATKIN_DEPENDS')
        if 'message_generation' in section.values:
            section.values.remove('message_generation')
            cmd.changed = True

    package.cmake.section_check(package.get_dependencies_from_msgs(), 'generate_messages',
                                'DEPENDENCIES', zero_okay=True)


@roscompile
def check_includes(package):
    has_includes = False
    if package.source_code.has_header_files():
        package.cmake.section_check(['include'], 'catkin_package', 'INCLUDE_DIRS')
        package.cmake.section_check(['include'], 'include_directories')
        has_includes = True

    if len(package.source_code.get_source_by_language('c++')) > 0:
        package.cmake.section_check(['${catkin_INCLUDE_DIRS}'], 'include_directories')
        has_includes = True

    if not has_includes and 'include_directories' in package.cmake.content_map:
        for cmd in package.cmake.content_map['include_directories']:
            package.cmake.remove_command(cmd)


@roscompile
def check_library_setup(package):
    package.cmake.section_check(package.cmake.get_libraries(), 'catkin_package', 'LIBRARIES')


def alphabetize_sections_helper(cmake):
    for content in cmake.contents:
        if content.__class__ == Command:
            for section in content.get_real_sections():
                if section.name in SHOULD_ALPHABETIZE:
                    section.values = sorted(section.values)
        elif content.__class__ == CommandGroup:
            alphabetize_sections_helper(content.sub)


@roscompile
def alphabetize_sections(package):
    alphabetize_sections_helper(package.cmake)


@roscompile
def prettify_catkin_package_cmd(package):
    for cmd in package.cmake.content_map['catkin_package']:
        for section in cmd.get_real_sections():
            section.style.prename = '\n    '
        cmd.changed = True


@roscompile
def prettify_package_lists(package):
    for cmd_name, section_name in [('find_package', 'COMPONENTS'), ('catkin_package', 'CATKIN_DEPENDS')]:
        for cmd in package.cmake.content_map[cmd_name]:
            for section in cmd.get_real_sections():
                if section.name != section_name:
                    continue
                n = len(str(section))
                if n > 120:
                    section.style.name_val_sep = '\n        '
                    section.style.val_sep = '\n        '
                    cmd.changed = True


@roscompile
def prettify_msgs_srvs(package):
    for cmd in package.cmake.content_map['add_message_files'] + package.cmake.content_map['add_service_files']:
        for section in cmd.get_real_sections():
            if len(section.values) > 1:
                section.style.name_val_sep = '\n    '
                section.style.val_sep = '\n    '
            cmd.changed = True


@roscompile
def prettify_installs(package):
    for cmd in package.cmake.content_map['install']:
        cmd.changed = True
        cmd.sections = [s for s in cmd.sections if type(s) != str]
        zeroed = False
        for section in cmd.sections[1:]:
            if len(section.values) == 0:
                section.style.prename = '\n        '
                zeroed = True
            elif not zeroed:
                section.style.prename = '\n        '
            else:
                section.style.prename = ''


def remove_empty_strings(a):
    return filter(lambda x: x != '', a)


def remove_cmake_command_comments_helper(command, ignorables, replacement=''):
    for i, section in enumerate(command.sections):
        if type(section) != str:
            continue
        for ignorable in ignorables:
            while ignorable in command.sections[i]:
                command.changed = True
                command.sections[i] = command.sections[i].replace(ignorable, replacement)
    if command.changed:
        command.sections = remove_empty_strings(command.sections)
        if command.sections == ['\n']:
            command.sections = []


def remove_cmake_comments_helper(cmake, ignorables, replacement=''):
    for i, content in enumerate(cmake.contents):
        if content.__class__ == Command:
            remove_cmake_command_comments_helper(content, ignorables, replacement)
        elif content.__class__ == CommandGroup:
            remove_cmake_comments_helper(content.sub, ignorables, replacement)
        else:
            for ignorable in ignorables:
                while ignorable in cmake.contents[i]:
                    cmake.contents[i] = cmake.contents[i].replace(ignorable, replacement)
    cmake.contents = remove_empty_strings(cmake.contents)


@roscompile
def remove_boilerplate_cmake_comments(package):
    ignorables = get_ignore_data('cmake', {'package': package.name})
    remove_cmake_comments_helper(package.cmake, ignorables)
    remove_empty_cmake_lines(package)


@roscompile
def remove_empty_cmake_lines(package):
    for i, content in enumerate(package.cmake.contents[:-2]):
        if str(content)[-1] == '\n' and package.cmake.contents[i + 1] == '\n' and package.cmake.contents[i + 2] == '\n':
            package.cmake.contents[i + 1] = ''
    package.cmake.contents = remove_empty_strings(package.cmake.contents)


def get_cmake_clusters(cmake):
    anchors = cmake.get_ordered_build_targets()
    clusters = []
    current = []
    for content in cmake.contents:
        current.append(content)
        if type(content) == str:
            continue
        key = get_sort_key(content, anchors)
        clusters.append((key, current))
        current = []
    if len(current) > 0:
        clusters.append((get_sort_key(None, anchors), current))

    return sorted(clusters, key=lambda (key, contents): key)


def enforce_cmake_ordering_helper(cmake):
    clusters = get_cmake_clusters(cmake)
    cmake.contents = []
    for key, contents in clusters:
        cmake.contents += contents


@roscompile
def enforce_cmake_ordering(package):
    enforce_cmake_ordering_helper(package.cmake)
    for group in package.cmake.content_map['group']:
        enforce_cmake_ordering_helper(group.sub)
