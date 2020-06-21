from ros_introspection.ros_generator import PRIMITIVES
from .util import roscompile

STANDARD = {
    'Header': 'std_msgs'
}

@roscompile
def fill_in_msg_package_names(package):
    all_names = set()
    gens = list(package.get_all_generators())
    for gen in gens:
        all_names.add(gen.base_name)
    for gen in gens:
        for section in gen.sections:
            for field in section.fields:
                if '/' in field.type or field.type in PRIMITIVES:
                    continue

                if field.type in STANDARD:
                    field.type = STANDARD[field.type] + '/' + field.type
                    gen.changed = True
                elif field.type in all_names:
                    field.type = package.name + '/' + field.type
                    gen.changed = True
