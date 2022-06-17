import os.path
import re

AT_LEAST_THREE_DASHES = re.compile(r'^\-{3,}\r?$')
FIELD_LINE = re.compile(r'([\w_/]+)(\[\d*\])?\s+([\w_]+)\s*(=.*)?(\s*\#.*)?$', re.DOTALL)
PRIMITIVES = ['bool', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64',
              'float32', 'float64', 'string', 'time', 'duration']


class GeneratorField:
    def __init__(self, field_type, is_array, name, value):
        self.type = field_type
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
        stripped = line.strip()
        if not stripped or stripped[0] == '#':
            self.contents.append(line)
            return
        m = FIELD_LINE.match(line)
        if m:
            field_type, is_array, name, value, comment = m.groups()
            field = GeneratorField(field_type, is_array, name, value)
            self.contents.append(field)
            self.fields.append(field)
            if comment:
                self.contents.append(comment)
            else:
                self.contents.append('\n')
        else:
            raise Exception('Unable to parse generator line: ' + repr(line))

    def __repr__(self):
        return ''.join(map(str, self.contents))


class ROSGenerator:
    def __init__(self, rel_fn, file_path):
        self.rel_fn = rel_fn
        self.file_path = file_path
        parts = os.path.splitext(rel_fn)
        self.base_name = os.path.split(parts[0])[-1]
        self.type = parts[-1][1:]  # Just the extension, no dot
        self.name = os.path.basename(rel_fn)
        self.changed = False
        self.sections = [GeneratorSection()]

        self.dependencies = set()

        with open(file_path) as f:
            self.contents = f.read()

        for line in self.contents.split('\n'):
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
