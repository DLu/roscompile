import collections
import os
import re

from ros_introspection.plugin_xml import PluginXML

from .manifest import enforce_tabbing_helper
from .util import roscompile

PLUGIN_PATTERN = r'PLUGINLIB_EXPORT_CLASS\(([^:]+)::([^,]+),\s*([^:]+)::([^,]+)\)'
PLUGIN_RE = re.compile(PLUGIN_PATTERN)


def plugin_xml_by_package(package):
    xmls = collections.defaultdict(list)
    for xml in package.plugin_configs:
        for parent_pkg in xml.parent_pkgs:
            xmls[parent_pkg].append(xml)
    return xmls


def contains_library(xmls, library, pkg, name):
    for xml in xmls:
        if xml.contains_library(library, pkg, name):
            return True
    return False


def lookup_library(build_rules, rel_fn):
    for library, deps in build_rules.items():
        if rel_fn in deps:
            return library


@roscompile
def check_plugins(package):
    """Check that all the plugins are properly defined.

    We have three dictionaries
      * The plugins that are defined by macros (defined_macros)
      * The plugins that have associated configuration files (existing_plugins)
      * The plugins that are linked by the manifest. (plugin_xml_by_package)
    First, we reconcile the macros with the files.
    Then we handle the manifest.
    Then we make sure that the specific classes are in the configurations
    """
    if not package.cmake:
        return
    defined_macros = package.source_code.search_for_pattern(PLUGIN_RE)
    existing_plugins = plugin_xml_by_package(package)
    defined_plugins = package.manifest.get_plugin_xmls()
    build_rules = package.cmake.get_source_build_rules('add_library', resolve_target_name=True)

    for rel_fn, plugin_info in defined_macros.items():
        library = lookup_library(build_rules, rel_fn)
        # pkg2/name2 is the parent class
        for pkg1, name1, pkg2, name2 in plugin_info:
            # Create file if needed
            if pkg2 not in existing_plugins:
                xml_filename = '%s_plugins.xml' % pkg2
                print('\tCreating %s' % xml_filename)
                p_xml = PluginXML(xml_filename, os.path.join(package.root, xml_filename))
                package.plugin_configs.append(p_xml)
                existing_plugins[pkg2] = [p_xml]

            # Make sure plugins are properly exported
            for plugin_xml in existing_plugins[pkg2]:
                if plugin_xml.rel_fn not in defined_plugins[pkg2]:
                    ex_el = package.manifest.add_plugin_export(pkg2, plugin_xml.rel_fn)
                    enforce_tabbing_helper(package.manifest, ex_el, 2)

            # Make sure the class is in the files
            if not contains_library(existing_plugins[pkg2], library, pkg1, name1):
                # insert into first
                xml = existing_plugins[pkg2][0]
                xml.insert_new_class(library, pkg1, name1, pkg2, name2)
