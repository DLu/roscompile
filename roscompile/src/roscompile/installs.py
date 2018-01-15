import os
import collections
from ros_introspection.cmake import Command
from util import roscompile

FILES_TO_NOT_INSTALL = ['CHANGELOG.rst', 'README.md']

# We define four install types, using a unique string to identify each (the keys in this dict)
# The values define a tuple, where the first element is a CMake keyword.
# The second value is a dictionary mapping catkin destinations to some CMake section names.
INSTALL_CONFIGS = {
    'exec': ('TARGETS', {'${CATKIN_PACKAGE_BIN_DESTINATION}': ['RUNTIME DESTINATION']}),
    'library': ('TARGETS', {'${CATKIN_PACKAGE_LIB_DESTINATION}': ['ARCHIVE DESTINATION', 'LIBRARY DESTINATION'],
                            '${CATKIN_GLOBAL_BIN_DESTINATION}': ['RUNTIME DESTINATION']}),
    'headers': ('FILES', {'${CATKIN_PACKAGE_INCLUDE_DESTINATION}': ['DESTINATION']}),
    'misc': ('FILES', {'${CATKIN_PACKAGE_SHARE_DESTINATION}': ['DESTINATION']})
}


def get_install_type(destination):
    """ For a given catkin destination, return the matching install type """
    for name, (kw, destination_map) in INSTALL_CONFIGS.iteritems():
        if destination in destination_map:
            return name


def get_install_types(cmd, subfolder=''):
    """ For a given CMake command, determine the install type(s) that this command uses.

        If there is a non-empty subfolder, we only return the install types if the command
        installs into the catkin_destination with the given subfolder """
    types = set()
    for section in cmd.get_sections('DESTINATION'):
        the_folder = section.values[0]
        if len(subfolder) > 0:
            if subfolder not in the_folder:
                continue
            the_folder = the_folder.replace('/' + subfolder, '')
        type_ = get_install_type(the_folder)
        if type_:
            types.add(type_)
    return types


def get_multiword_section(cmd, words):
    """ Our definition of a CMake command section is ONE all-caps word followed by tokens.
        Installing stuff requires these weird TWO word sections (i.e. ARCHIVE DESTINATION).

        Ergo, we need to find the section that matches the second word, presuming the section
        before matched the first word.
    """
    i = 0
    for section in cmd.get_real_sections():
        if section.name == words[i]:
            # One word matches
            if i < len(words) - 1:
                # If there are more words, increment the counter
                i += 1
            else:
                # Otherwise, we matched all the words. Return this section
                return section
        else:
            # If the word doesn't match, we need to start searching from the first word again
            i = 0


def check_complex_section(cmd, key, value):
    """ This finds the appopriate section of the command (with a possibly multiword key, see get_multiword_section)
        and ensures the given value is in it. If the appopriate section is not found, it adds it. """

    words = key.split()
    if len(words) == 1:
        section = cmd.get_section(key)
    else:
        section = get_multiword_section(cmd, words)

    if section:
        if value not in section.values:
            section.add(value)
            cmd.changed = True
    else:
        cmd.add_section(key, [value])


def install_sections(cmd, destination_map, subfolder=''):
    """ For a given command and destination_map, ensure that the command has all
        the appropriate CMake sections with the matching catkin destinations.
        If the subfolder is defined, the subfolder is appended to the catkin destination."""
    for destination, section_names in destination_map.iteritems():
        for section_name in section_names:
            if len(subfolder) > 0:
                destination = os.path.join(destination, subfolder)
            check_complex_section(cmd, section_name, destination)


def remove_install_section(cmd, destination_map):
    empty_sections_to_remove = {}
    for destination, section_names in destination_map.iteritems():
        for section_name in section_names:
            parts = section_name.split()
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


def get_commands_by_type(cmake, name, subfolder=''):
    matches = []
    for cmd in cmake.content_map['install']:
        if name in get_install_types(cmd, subfolder):
            matches.append(cmd)
    return matches


def install_section_check(cmake, items, install_type, directory=False, subfolder=''):
    section_name, destination_map = INSTALL_CONFIGS[install_type]
    if directory and section_name == 'FILES':
        section_name = 'DIRECTORY'
    cmds = get_commands_by_type(cmake, install_type, subfolder)
    if len(items) == 0:
        for cmd in cmds:
            if len(get_install_types(cmd)) == 1:
                cmake.remove_command(cmd)
            else:
                remove_install_section(cmd, destination_map)
        return

    cmd = None
    for cmd in cmds:
        install_sections(cmd, destination_map, subfolder)
        section = cmd.get_section(section_name)
        if not section:
            continue
        section.values = [value for value in section.values if value in items]
        items = [item for item in items if item not in section.values]

    if len(items) == 0:
        return

    print '\tInstalling', ', '.join(items)
    if cmd is None:
        cmd = Command('install')
        cmd.add_section(section_name, items)
        cmake.add_command(cmd)
        install_sections(cmd, destination_map, subfolder)
    elif section:
        section = cmd.get_section(section_name)
        section.values += items
        section.changed = True


@roscompile
def update_cplusplus_installs(package):
    install_section_check(package.cmake, package.cmake.get_executables(), 'exec')
    install_section_check(package.cmake, package.cmake.get_libraries(), 'library')
    if package.name and package.source_code.has_header_files():
        install_section_check(package.cmake, ['include/${PROJECT_NAME}/'], 'headers', directory=True)


@roscompile
def update_misc_installs(package):
    extra_files_by_folder = collections.defaultdict(list)
    rel_paths = [obj.rel_fn for obj in package.launches + package.plugin_configs] + package.misc_files
    for rel_path in sorted(rel_paths):
        if rel_path in FILES_TO_NOT_INSTALL:
            continue
        path, base = os.path.split(rel_path)
        extra_files_by_folder[path].append(base)

    for folder, files in extra_files_by_folder.iteritems():
        install_section_check(package.cmake, files, 'misc', subfolder=folder)
