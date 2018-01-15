import os.path
import re

AT_LEAST_THREE_DASHES = re.compile('^\-{3,}$')


class ROSGenerator:
    def __init__(self, rel_fn, file_path):
        self.file_path = file_path
        parts = os.path.splitext(rel_fn)
        self.base_name = os.path.split(parts[0])[-1]
        self.type = parts[-1][1:]  # Just the extension, no dot
        self.name = os.path.basename(rel_fn)

        self.dependencies = set()

        with open(file_path) as f:
            for line in f:
                if '#' in line:
                    line = line[:line.index('#')]
                line = line.strip()
                if AT_LEAST_THREE_DASHES.match(line) or line == '':
                    continue
                if '=' in line.split():
                    line = line[:line.index('=')]
                tipo, name = line.split()
                if '/' not in tipo:
                    continue
                package, part = tipo.split('/')
                if package != self.name:
                    self.dependencies.add(package)

        if self.type == 'action':
            self.dependencies.add('actionlib_msgs')

    def __repr__(self):
        return self.name
