from ros_introspection.package_xml import DEPEND_ORDERING

from .util import REPLACE_PACKAGES


def set_build_type(manifest, build_type):
    ex_el = manifest.get_export_tag()
    build_type_node = ex_el.getElementsByTagName('build_type')
    if build_type_node:
        pass
    else:
        built_type_tag = manifest.tree.createElement('build_type')
        built_type_tag.appendChild(manifest.tree.createTextNode(build_type))
        manifest.insert_new_tag_inside_another(ex_el, built_type_tag)

    if build_type != 'ament_cmake':
        return

    for build_tool in manifest.root.getElementsByTagName('buildtool_depend'):
        name = build_tool.childNodes[0].nodeValue
        if name == 'catkin':
            build_tool.childNodes[0] = manifest.tree.createTextNode(build_type)


def update_manifest(package):
    manifest = package.manifest
    if manifest.format < 2:
        manifest.upgrade(2)

    # Remove metapackage tag
    pairs = []
    for export_tag in manifest.tree.getElementsByTagName('export'):
        for child in export_tag.childNodes:
            if child.nodeType == child.ELEMENT_NODE and child.nodeName == 'metapackage':
                pairs.append((export_tag, child))
    for parent, child in pairs:
        parent.removeChild(child)
        manifest.changed = True

    # Replace some packages
    for old_and_busted, new_hotness in REPLACE_PACKAGES.items():
        for tag_name in DEPEND_ORDERING:
            pkgs = package.manifest.get_packages_by_tag(tag_name)
            if old_and_busted in pkgs:
                package.manifest.remove_dependencies(tag_name, [old_and_busted])
                if new_hotness not in pkgs:
                    package.manifest.insert_new_packages(tag_name, [new_hotness])
