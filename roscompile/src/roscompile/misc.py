import re
import os
from util import roscompile, make_executable
from ros_introspection.util import get_packages

MAINPAGE_S = "/\*\*\s+\\\\mainpage\s+\\\\htmlinclude manifest.html\s+\\\\b %s\s+<!--\s+" + \
             "Provide an overview of your package.\s+-->\s+-->\s+[^\*]*\*/"


@roscompile
def check_dynamic_reconfigure(package):
    cfgs = package.dynamic_reconfigs
    if len(cfgs) == 0:
        return
    pkg_list = set(['dynamic_reconfigure'])
    package.manifest.add_packages(pkg_list, pkg_list)
    package.cmake.section_check(cfgs, 'generate_dynamic_reconfigure_options', '')
    package.cmake.section_check(pkg_list, 'find_package', 'COMPONENTS')

    for fn in cfgs:
        make_executable(os.path.join(package.root, fn))


@roscompile
def remove_useless_files(package):
    mainpage_pattern = re.compile(MAINPAGE_S % package.name)
    for fn in package.misc_files:
        if 'mainpage.dox' in fn:
            full_path = os.path.join(package.root, fn)
            s = open(full_path).read()
            if mainpage_pattern.match(s):
                os.remove(full_path)


@roscompile
def update_metapackage(package, require_matching_name=False):
    # TODO: Check if metapackage is in CMake
    # TODO: Ensure export is in there too
    if not package.manifest.is_metapackage():
        return False

    parent_path = os.path.abspath(os.path.join(package.root, '..'))

    if require_matching_name and os.path.split(parent_path)[1] != package.name:
        return False

    sub_packages = set()
    for sub_package in get_packages(parent_path, create_objects=False):
        pkg_name = os.path.split(sub_package)[1]
        if pkg_name != package.name:
            sub_packages.add(pkg_name)
    existing_sub_packages = package.manifest.get_packages('run')
    package.manifest.add_packages(set(), sub_packages, prefer_depend_tag=False)

    if package.manifest.format == 1:
        pkg_type = 'run_depend'
    else:
        pkg_type = 'exec_depend'

    package.manifest.remove_dependencies(pkg_type, existing_sub_packages - sub_packages)
    package.cmake.section_check([], 'catkin_metapackage', zero_okay=True)


@roscompile
def misc_xml_formatting(package):
    package.manifest.changed = True
    for config in package.plugin_configs:
        config.changed = True

