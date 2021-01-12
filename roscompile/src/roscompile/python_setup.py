import os

from ros_introspection.cmake import Command, SectionStyle
from ros_introspection.setup_py import SetupPy

from .cmake import CATKIN_INSTALL_PYTHON_PRENAME
from .util import roscompile


def has_python(package):
    return len(package.source_code.get_source_by_language('python')) > 0


def has_python_library(package):
    key = 'src/%s' % package.name
    for source in package.source_code.get_source_by_language('python'):
        if key in source.rel_fn:
            return True
    return False


@roscompile
def check_setup_py(package):
    if not has_python(package):
        return
    if package.setup_py is None:
        if not has_python_library(package):
            # No library, and no existing setup_py means nothing to write
            return
        package.setup_py = SetupPy(package.name, os.path.join(package.root, 'setup.py'))

    if 'catkin_python_setup' not in package.cmake.content_map:
        package.cmake.add_command(Command('catkin_python_setup'))


@roscompile
def update_python_installs(package):
    execs = [source.rel_fn for source in package.source_code.get_source_by_language('python') if source.is_executable()]
    if len(execs) == 0:
        return
    cmd = 'catkin_install_python'
    if cmd not in package.cmake.content_map:
        cmake_cmd = Command(cmd)
        cmake_cmd.add_section('PROGRAMS', execs)
        cmake_cmd.add_section('DESTINATION', ['${CATKIN_PACKAGE_BIN_DESTINATION}'],
                              SectionStyle(CATKIN_INSTALL_PYTHON_PRENAME))
        package.cmake.add_command(cmake_cmd)
    else:
        package.cmake.section_check(execs, cmd, 'PROGRAMS')
