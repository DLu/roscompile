from .util import REPLACE_PACKAGES


def set_build_type(manifest, build_type):
    ex_el = manifest.get_export_tag()
    built_type_tag = manifest.tree.createElement('build_type')
    built_type_tag.appendChild(manifest.tree.createTextNode(build_type))
    manifest.insert_new_tag_inside_another(ex_el, built_type_tag)

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
        if old_and_busted in package.manifest.get_packages():
            package.manifest.remove_dependencies('depend', [old_and_busted])
            if new_hotness not in package.manifest.get_packages():
                package.manifest.insert_new_packages('depend', [new_hotness])
