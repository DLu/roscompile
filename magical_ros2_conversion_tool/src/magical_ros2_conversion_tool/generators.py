from ros_introspection.cmake import Command, SectionStyle

BUILTIN_INTERFACES = {
    'duration': 'builtin_interfaces/Duration',
    'time': 'builtin_interfaces/Time'
}


def fix_generator_definition(gen):
    for section in gen.sections:
        for field in section.fields:
            if field.type in BUILTIN_INTERFACES:
                field.type = BUILTIN_INTERFACES[field.type]
                gen.changed = True
            elif field.type == 'Header':
                field.type = 'std_msgs/Header'
                gen.changed = True


def update_generators(package):
    if not package.generators:
        return

    for gen in package.get_all_generators():
        fix_generator_definition(gen)

    # Update Dependencies
    package.manifest.insert_new_packages('buildtool_depend', ['rosidl_default_generators'])
    package.manifest.insert_new_packages('exec_depend', ['rosidl_default_runtime'])
    if package.manifest.format < 3:
        package.manifest.upgrade(3)
    package.manifest.insert_new_packages('member_of_group', ['rosidl_interface_packages'])

    # Enabling C++14
    cxx_name = 'CMAKE_CXX_STANDARD'
    cxx_value = '14'
    if cxx_name in package.cmake.variables:
        for cmd in package.cmake.content_map['set']:
            tokens = cmd.get_tokens(include_name=True)
            if tokens[0] == cxx_name and tokens[1] != cxx_value:
                cmd.sections[0].values = [cxx_value]
                cmd.changed = True
    else:
        set_cmd = Command('set')
        set_cmd.add_section(cxx_name, cxx_value)
        package.cmake.add_command(set_cmd)

    # Other msg operations
    fp = Command('find_package')
    fp.add_section('', ['rosidl_default_generators'])
    fp.add_section('REQUIRED')
    package.cmake.add_command(fp)

    my_style = SectionStyle('\n    ', '\n        ', '\n        ')
    idl = Command('rosidl_generate_interfaces')
    generator_paths = [gen.type + '/' + gen.name for gen in package.get_all_generators()]
    idl.add_section('', ['${PROJECT_NAME}'] + generator_paths, my_style)
    idl.add_section('DEPENDENCIES', package.get_dependencies_from_msgs(), my_style)
    package.cmake.add_command(idl)

    for old_cmd_name in ['add_message_files', 'add_service_files', 'generate_messages']:
        for cmd in package.cmake.content_map[old_cmd_name]:
            package.cmake.remove_command(cmd)
