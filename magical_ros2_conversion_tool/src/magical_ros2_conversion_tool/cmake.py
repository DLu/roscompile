from ros_introspection.cmake import Command, is_testing_group

from roscompile.cmake import enforce_cmake_ordering, remove_empty_cmake_lines

from .util import REPLACE_PACKAGES


CATKIN_CMAKE_VARS = {
    '${CATKIN_GLOBAL_BIN_DESTINATION}': 'bin',
    '${CATKIN_GLOBAL_INCLUDE_DESTINATION}': 'include',
    '${CATKIN_GLOBAL_LIB_DESTINATION}': 'lib',
    '${CATKIN_GLOBAL_LIBEXEC_DESTINATION}': 'lib',
    '${CATKIN_GLOBAL_SHARE_DESTINATION}': 'share',
    '${CATKIN_PACKAGE_BIN_DESTINATION}': 'lib/${PROJECT_NAME}',
    '${CATKIN_PACKAGE_INCLUDE_DESTINATION}': 'include/${PROJECT_NAME}',
    '${CATKIN_PACKAGE_LIB_DESTINATION}': 'lib',
    '${CATKIN_PACKAGE_SHARE_DESTINATION}': 'share/${PROJECT_NAME}',
}


def split_find_package_commands(cmake):
    """Convert find_package commands to find one package at a time."""
    components = ['ament_cmake']
    for cmd in cmake.content_map['find_package']:
        tokens = cmd.get_tokens()
        if not tokens or tokens[0] != 'catkin':
            continue
        if cmd.get_section('REQUIRED'):
            cmps = cmd.get_section('COMPONENTS')
            if cmps:
                components += cmps.values

        cmake.remove_command(cmd)

    for component in components:
        if component == 'message_generation':
            continue
        if component in REPLACE_PACKAGES:
            component = REPLACE_PACKAGES[component]
        cmd = Command('find_package')
        cmd.add_section('', [component])
        cmd.add_section('REQUIRED')
        cmake.add_command(cmd)


def catkin_to_ament_package(package):
    if not package.cmake.content_map['catkin_package']:
        return

    pkg_cmd = package.cmake.content_map['catkin_package'][0]
    for sname, cmd_name in [('CATKIN_DEPENDS', 'ament_export_dependencies'),
                            ('INCLUDE_DIRS', 'ament_export_include_directories'),
                            ('LIBRARIES', 'ament_export_libraries')]:
        section = pkg_cmd.get_section(sname)
        if not section:
            continue
        no_cpp = len(package.source_code.get_source_by_language('c++'))
        if sname == 'CATKIN_DEPENDS' and no_cpp == 0 and 'message_runtime' in section.values:
            continue
        cmd = Command(cmd_name)
        cmd.add_section('', [REPLACE_PACKAGES.get(k, k) for k in section.values])
        package.cmake.add_command(cmd)

    cmd = Command('ament_package')
    package.cmake.add_command(cmd)


def update_installation_variables(cmake):
    for cmd in cmake.content_map['install']:
        for section in cmd.get_sections('DESTINATION'):
            for i, value in enumerate(section.values):
                if value in CATKIN_CMAKE_VARS:
                    section.values[i] = CATKIN_CMAKE_VARS[value]
                    cmd.changed = True


def remove_cpp11_flag(cmake):
    to_remove = []
    for cmd in cmake.content_map['set_directory_properties']:
        section = cmd.get_section('COMPILE_OPTIONS')
        bits = list(filter(None, section.values[0][1:-1].split(';')))
        if '-std=c++11' in bits:
            bits.remove('-std=c++11')
        if len(bits) == 0:
            to_remove.append(cmd)
        else:
            section.values = ['"%s"' % ';'.join(bits)]
            cmd.changed = True
    for cmd in to_remove:
        cmake.remove_command(cmd)


def get_clean_build_dependencies(package):
    return [REPLACE_PACKAGES.get(k, k) for k in package.source_code.get_build_dependencies()]


def set_up_include_exports(package):
    cat_var = '${catkin_INCLUDE_DIRS}'
    # TODO: Probably remove? dirs = ['${%s_INCLUDE_DIRS}' % s for s in get_clean_build_dependencies(package)]
    for cmd in package.cmake.content_map['include_directories']:
        section = cmd.sections[0]
        if cat_var in section.values:
            section.values.remove(cat_var)
            cmd.changed = True


def rename_commands(cmake, source_name, target_name, remove_sections=[]):
    for cmd in cmake.content_map[source_name]:
        cmd.command_name = target_name
        cmd.changed = True
        for name in remove_sections:
            cmd.remove_sections(name)
    cmake.content_map[target_name] = cmake.content_map[source_name]
    del cmake.content_map[source_name]


def set_up_catkin_libs(package):
    deps = ['"{}"'.format(s) for s in get_clean_build_dependencies(package)]

    cat_var = '${catkin_LIBRARIES}'
    rename_commands(package.cmake, 'target_link_libraries', 'ament_target_dependencies')
    for cmd in package.cmake.content_map['ament_target_dependencies']:
        for section in cmd.get_real_sections():
            if cat_var in section.values:
                section.values.remove(cat_var)
                section.values += deps
                cmd.changed = True


def update_tests(package):
    for content in package.cmake.content_map['group']:
        if is_testing_group(content):
            content.initial_tag.sections[0].name = 'BUILD_TESTING'
            content.initial_tag.changed = True
            rename_commands(content.sub, 'catkin_add_gtest', 'ament_add_gtest')

    rename_commands(package.cmake, 'catkin_add_gtest', 'ament_add_gtest')


def update_cmake(package):
    package.cmake.upgrade_minimum_version((3, 5))
    split_find_package_commands(package.cmake)
    catkin_to_ament_package(package)
    update_installation_variables(package.cmake)
    remove_cpp11_flag(package.cmake)
    set_up_include_exports(package)
    set_up_catkin_libs(package)
    update_tests(package)

    # Remove deprecated Commands
    for old_cmd_name in ['catkin_python_setup', 'add_dependencies', 'catkin_package']:
        package.cmake.remove_all_commands(old_cmd_name)
    enforce_cmake_ordering(package)
    remove_empty_cmake_lines(package)
