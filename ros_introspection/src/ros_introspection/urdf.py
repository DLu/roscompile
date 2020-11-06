import re

FIND_PATTERN = re.compile(r'\$\(find ([^\)]+)\)')
PACKAGE_PATTERN = re.compile(r'package://([^/]+)/')


class UrdfFile:
    def __init__(self, rel_fn, file_path):
        self.rel_fn = rel_fn
        self.file_path = file_path
        self.contents = open(file_path).read()

    def get_dependencies(self):
        s = set()
        for pattern in [FIND_PATTERN, PACKAGE_PATTERN]:
            for match in pattern.findall(self.contents):
                s.add(match)
        return sorted(s)

    def __repr__(self):
        return self.rel_fn
