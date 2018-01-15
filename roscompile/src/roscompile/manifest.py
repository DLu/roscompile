from ros_introspection.package_xml import count_trailing_spaces, get_ordering_index
from util import get_ignore_data, roscompile, get_config


@roscompile
def check_manifest_dependencies(package):
    build_depends = package.get_build_dependencies()
    run_depends = package.get_run_dependencies()
    test_depends = package.get_test_dependencies()
    package.manifest.add_packages(build_depends, run_depends, test_depends)

    if package.generators:
        md = package.get_dependencies_from_msgs()
        package.manifest.add_packages(md, md)

        if package.manifest.format == 1:
            pairs = [('build_depend', 'message_generation'),
                     ('run_depend', 'message_runtime')]
        else:
            pairs = [('build_depend', 'message_generation'),
                     ('build_export_depend', 'message_runtime'),
                     ('exec_depend', 'message_runtime')]
            package.manifest.remove_dependencies('depend', ['message_generation', 'message_runtime'])
        for tag, msg_pkg in pairs:
            existing = package.manifest.get_packages_by_tag(tag)
            if msg_pkg not in existing:
                package.manifest.insert_new_packages(tag, [msg_pkg])


def has_element_child(node):
    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            return True
    return False


@roscompile
def remove_empty_export_tag(package):
    exports = package.manifest.root.getElementsByTagName('export')
    if len(exports) == 0:
        return False
    for export in exports:
        if not has_element_child(export):
            package.manifest.remove_element(export)
            return True
            # print '\tRemoving empty export tag'


def replace_package_set(manifest, source_tags, new_tag):
    """
       Find the set of packages that are defined in the manifest using all of the tags listed in source_tags.
       Remove all those elements and replace them with the new_tag.
    """
    intersection = None
    for tag in source_tags:
        pkgs = set(manifest.get_packages_by_tag(tag))
        if intersection is None:
            intersection = pkgs
        else:
            intersection = intersection.intersection(pkgs)
    for tag in source_tags:
        manifest.remove_dependencies(tag, intersection)
    manifest.insert_new_packages(new_tag, intersection)


@roscompile
def greedy_depend_tag(package):
    if package.manifest.format == 1:
        return
    replace_package_set(package.manifest, ['build_depend', 'build_export_depend', 'exec_depend'], 'depend')


def enforce_tabbing_helper(manifest, node, tabs=1):
    ideal_length = manifest.std_tab * tabs
    prev_was_node = True
    insert_before_list = []
    for c in node.childNodes:
        if c.nodeType == c.TEXT_NODE:
            prev_was_node = False
            if c == node.childNodes[-1]:
                continue
            spaces = count_trailing_spaces(c.data)
            if spaces > ideal_length:
                c.data = c.data[: ideal_length - spaces]
            elif spaces < ideal_length:
                c.data = c.data + ' ' * (ideal_length - spaces)
            if '\n' not in c.data:
                c.data = '\n' + c.data
        elif prev_was_node:
            insert_before_list.append(c)
        else:
            prev_was_node = True

    for c in insert_before_list:
        node.insertBefore(manifest.get_tab_element(tabs), c)

    if len(node.childNodes) == 0:
        return
    last = node.childNodes[-1]
    if last.nodeType != last.TEXT_NODE:
        node.appendChild(manifest.get_tab_element(tabs - 1))


@roscompile
def enforce_manifest_tabbing(package):
    enforce_tabbing_helper(package.manifest, package.manifest.root)


def get_sort_key(node, alphabetize_depends=True):
    if node:
        name = node.nodeName
    else:
        name = None

    index = get_ordering_index(name)

    if not alphabetize_depends:
        return index
    if name and 'depend' in name:
        return index, node.firstChild.data
    else:
        return index, None


def get_chunks(children):
    """ Given the children, group the elements into tuples that are
        (an element node, [(some number of text nodes), that element node again])
    """
    chunks = []
    current = []
    for child_node in children:
        current.append(child_node)
        if child_node.nodeType == child_node.ELEMENT_NODE:
            chunks.append((child_node, current))
            current = []
    if len(current) > 0:
        chunks.append((None, current))
    return chunks


@roscompile
def enforce_manifest_ordering(package, alphabetize=True):
    root = package.manifest.root
    chunks = get_chunks(root.childNodes)

    root.childNodes = []

    for a, b in sorted(chunks, key=lambda d: get_sort_key(d[0], alphabetize)):
        root.childNodes += b


def cleanup_text_elements(node):
    new_children = []

    for child in node.childNodes:
        if child.nodeType == child.TEXT_NODE and len(new_children) and new_children[-1].nodeType == child.TEXT_NODE:
            new_children[-1].data += child.data
        elif child.nodeType == child.TEXT_NODE and child.data == '':
            continue
        else:
            new_children.append(child)

    node.childNodes = new_children


def replace_text_node_contents(node, ignorables):
    removable = []
    for i, c in enumerate(node.childNodes):
        if c.nodeType == c.TEXT_NODE:
            continue
        elif c.nodeType == c.COMMENT_NODE:
            short = c.data.strip()
            if short in ignorables:
                removable.append(i)
                continue
        else:
            replace_text_node_contents(c, ignorables)
    for node_index in reversed(removable):  # backwards not to affect earlier indices
        if node_index > 0:
            before = node.childNodes[node_index - 1]
            if before.nodeType == c.TEXT_NODE:
                trailing = count_trailing_spaces(before.data)
                before.data = before.data[:-trailing]

        if node_index < len(node.childNodes) - 1:
            after = node.childNodes[node_index + 1]
            if after.nodeType == c.TEXT_NODE:
                while len(after.data) and after.data[0] == ' ':
                    after.data = after.data[1:]
                if len(after.data) and after.data[0] == '\n':
                    after.data = after.data[1:]

        node.childNodes.remove(node.childNodes[node_index])
    cleanup_text_elements(node)


@roscompile
def remove_boilerplate_manifest_comments(package):
    ignorables = get_ignore_data('package', {'package': package.name}, add_newline=False)
    replace_text_node_contents(package.manifest.root, ignorables)
    remove_empty_manifest_lines(package)


def remove_empty_lines_helper(node):
    for child in node.childNodes:
        if child.nodeType == child.TEXT_NODE:
            while '\n\n\n' in child.data:
                child.data = child.data.replace('\n\n\n', '\n\n')
        else:
            remove_empty_lines_helper(child)


@roscompile
def remove_empty_manifest_lines(package):
    remove_empty_lines_helper(package.manifest.root)


@roscompile
def update_people(package, config=None):
    if config is None:
        config = get_config()
    for d in config.get('replace_rules', []):
        package.manifest.update_people(d['to']['name'], d['to']['email'],
                                       d['from'].get('name', None), d['from'].get('email', None))


@roscompile
def update_license(package, config=None):
    if config is None:
        config = get_config()
    if 'default_license' not in config or package.manifest.get_license() != 'TODO':
        return

    package.manifest.set_license(config['default_license'])
