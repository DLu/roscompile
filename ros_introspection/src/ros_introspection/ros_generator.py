import os.path
import re

AT_LEAST_THREE_DASHES = re.compile('^\-{3,}$')
FIELD_LINE = re.compile('([\w_/]+)(\[\d*\])?\s+([\w_]+)(=.*)?(\s*\#.*)?$', re.DOTALL)


class GeneratorField:
    def __init__(self, type, is_array, name, value):
        self.type = type
        self.is_array = is_array
        self.name = name
        self.value = value

    def __repr__(self):
        s = self.type
        if self.is_array:
            s += '[]'
        s += ' '
        s += self.name
        if self.value:
            s += '='
            s += self.value
        return s


class GeneratorSection:
    def __init__(self):
        self.contents = []
        self.fields = []

    def add_line(self, line):
        if line[0] == '#' or line == '\n':
            self.contents.append(line)
            return
        m = FIELD_LINE.match(line)
        if m:
            type, is_array, name, value, comment = m.groups()
            field = GeneratorField(type, is_array, name, value)
            self.contents.append(field)
            self.fields.append(field)
            if comment:
                self.contents.append(comment)
            else:
                self.contents.append('\n')
        else:
            print repr(line)
            exit(0)

    def __repr__(self):
        return ''.join(map(str, self.contents))


class ROSGenerator:
    def __init__(self, rel_fn, file_path):
        self.file_path = file_path
        parts = os.path.splitext(rel_fn)
        self.base_name = os.path.split(parts[0])[-1]
        self.type = parts[-1][1:]  # Just the extension, no dot
        self.name = os.path.basename(rel_fn)
        self.changed = False
        self.sections = [GeneratorSection()]

        self.dependencies = set()

        with open(file_path) as f:
            for line in f:
                if AT_LEAST_THREE_DASHES.match(line):
                    self.sections.append(GeneratorSection())
                    continue
                else:
                    self.sections[-1].add_line(line)

        for section in self.sections:
            for field in section.fields:
                if '/' not in field.type:
                    continue
                package, part = field.type.split('/')
                if package != self.name:
                    self.dependencies.add(package)

        if self.type == 'action':
            self.dependencies.add('actionlib_msgs')

    def output(self):
        return '---\n'.join(map(str, self.sections))

    def write(self):
        if not self.changed:
            return
        with open(self.file_path, 'w') as f:
            f.write(self.output())

    def __repr__(self):
        return self.name
