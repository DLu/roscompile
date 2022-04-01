import yaml
import ruamel.yaml  # For custom yaml dumping


my_yaml_writer = ruamel.yaml.YAML()
my_yaml_writer.indent(mapping=2, sequence=4, offset=2)
my_yaml_writer.representer.add_representer(type(None),
                                           lambda self, data:
                                           self.represent_scalar('tag:yaml.org,2002:null', '~')
                                           )


def get_class_dicts(entry):
    classes = []
    if isinstance(entry, list):
        for sub in entry:
            classes += get_class_dicts(sub)
    elif isinstance(entry, dict):
        if entry.get('Class'):
            classes.append(entry)
        for k, v in entry.items():
            classes += get_class_dicts(v)
    return classes


def dictionary_subtract(alpha, beta):
    changed = False
    for k in beta.keys():
        if k not in alpha:
            continue
        v = alpha[k]
        if isinstance(v, dict):
            changed |= dictionary_subtract(v, beta[k])
            if not v:
                del alpha[k]
                changed = True
        elif v == beta[k]:
            del alpha[k]
            changed = True
    return changed


class RVizConfig:
    def __init__(self, rel_fn, path):
        self.rel_fn = rel_fn
        self.path = path
        self.contents = yaml.safe_load(open(path))
        self.changed = False

    def get_class_dicts(self):
        return get_class_dicts(self.contents)

    def get_dependencies(self):
        packages = set()
        for config in self.get_class_dicts():
            value = config['Class'].split('/')[0]
            packages.add(value)
        return packages

    def write(self):
        if not self.changed:
            return
        with open(self.path, 'w') as f:
            my_yaml_writer.dump(self.contents, f, transform=lambda s: s.replace(": ''\n", ': ""\n'))
