import os
import re
import yaml

from ros_introspection.rviz_config import dictionary_subtract
from ros_introspection.util import get_sibling_packages

from .util import PKG_PATH, make_executable, roscompile

MAINPAGE_S = r'/\*\*\s+\\mainpage\s+\\htmlinclude manifest.html\s+\\b %s\s+<!--\s+' + \
             r'Provide an overview of your package.\s+-->\s+-->\s+[^\*]*\*/'

RVIZ_CLASS_DEFAULTS = yaml.safe_load(open(PKG_PATH + '/data/rviz_class_defaults.yaml'))
RVIZ_GLOBAL_DEFAULTS = yaml.safe_load(open(PKG_PATH + '/data/rviz_global_defaults.yaml'))
ROBOT_MODEL_LINK_DEFAULTS = {'Alpha': 1, 'Show Axes': False, 'Show Trail': False, 'Value': True}


@roscompile
def check_dynamic_reconfigure(package):
    cfgs = package.dynamic_reconfigs
    if len(cfgs) == 0:
        return
    pkg_list = {'dynamic_reconfigure'}
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
def update_metapackage(package, sibling_packages=None, require_matching_name=False):
    # Check if there is indication in package.xml or CMake of being a metapackage
    if not package.is_metapackage():
        return False

    if require_matching_name:
        parent_path = os.path.abspath(os.path.join(package.root, '..'))

        if os.path.split(parent_path)[1] != package.name:
            return False

    if sibling_packages is None:
        sibling_packages = get_sibling_packages(package)

    existing_sub_packages = package.manifest.get_packages('run')
    package.manifest.add_packages(set(), sibling_packages, prefer_depend_tag=False)

    if package.manifest.format == 1:
        pkg_type = 'run_depend'
    else:
        pkg_type = 'exec_depend'

    package.manifest.remove_dependencies(pkg_type, existing_sub_packages - sibling_packages)

    # Ensure proper commands in CMake
    package.cmake.section_check([], 'catkin_metapackage', zero_okay=True)

    # Ensure proper tags in package.xml
    if not package.manifest.is_metapackage():
        export_tag = package.manifest.get_export_tag()
        meta_tag = package.manifest.tree.createElement('metapackage')
        package.manifest.insert_new_tag_inside_another(export_tag, meta_tag)


@roscompile
def misc_xml_formatting(package):
    package.manifest.changed = True
    for config in package.plugin_configs:
        config.changed = True


@roscompile
def clean_up_rviz_configs(package):
    for rviz_config in package.rviz_configs:
        for config in rviz_config.get_class_dicts():
            the_defaults = RVIZ_CLASS_DEFAULTS.get(config['Class'], {})
            if dictionary_subtract(config, the_defaults):
                rviz_config.changed = True

            # Special Case(s)
            if config['Class'] == 'rviz_default_plugins/RobotModel':
                for k, v in list(config.get('Links', {}).items()):
                    if not isinstance(v, dict):
                        continue
                    if dictionary_subtract(config['Links'][k], ROBOT_MODEL_LINK_DEFAULTS):
                        rviz_config.changed = True
                        if not config['Links'][k]:
                            del config['Links'][k]

            if config['Class'] == 'rviz/Camera' and 'Visibility' in config:
                visibility = config['Visibility']
                for key in list(visibility.keys()):
                    if visibility[key]:
                        rviz_config.changed = True
                        del visibility[key]
                if not visibility:
                    del config['Visibility']
        if dictionary_subtract(rviz_config.contents, RVIZ_GLOBAL_DEFAULTS):
            rviz_config.changed = True
