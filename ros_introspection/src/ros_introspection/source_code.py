import os.path
from source_code_file import SourceCodeFile


class SourceCode:
    def __init__(self, filenames, pkg_name):
        self.pkg_name = pkg_name
        self.sources = {}
        for rel_fn, file_path in filenames.iteritems():
            self.sources[rel_fn] = SourceCodeFile(rel_fn, file_path)

    def has_header_files(self):
        goal_folder = os.path.join('include', self.pkg_name)
        for source_fn in self.sources:
            if goal_folder in source_fn:
                return True
        return False

    def get_source_by_language(self, language):
        return [source for source in self.sources.values() if source.language == language]

    def setup_tags(self, cmake):
        for tag, files in [('library', cmake.get_library_source()),
                           ('executable', cmake.get_executable_source()),
                           ('test', cmake.get_test_source())]:
            for fn in files:
                if fn in self.sources:
                    self.sources[fn].tags.add(tag)
                else:
                    print '    File %s found in CMake not found in folder!' % fn

    def get_build_dependencies(self):
        packages = set()
        for source in self.sources.values():
            if 'test' in source.tags:
                continue
            packages.update(source.get_dependencies())
        if self.pkg_name in packages:
            packages.remove(self.pkg_name)
        return packages

    def get_external_python_dependencies(self):
        packages = set()
        for source in self.sources.values():
            if 'test' in source.tags:
                continue
            packages.update(source.get_external_python_dependencies())
        return packages

    def get_test_dependencies(self):
        packages = set()
        for source in self.sources.values():
            if 'test' not in source.tags:
                continue
            packages.update(source.get_dependencies())
        if self.pkg_name in packages:
            packages.remove(self.pkg_name)
        return packages

    def search_for_patterns(self, patterns):
        files = {}
        for source in self.sources.values():
            matches = source.search_lines_for_patterns(patterns)
            if len(matches) != 0:
                files[source.rel_fn] = matches
        return files

    def search_for_pattern(self, pattern):
        return self.search_for_patterns([pattern])

    def __repr__(self):
        return '\n'.join(map(str, sorted(self.sources.values())))
