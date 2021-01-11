import os.path

from .source_code_file import SourceCodeFile


class SourceCode:
    def __init__(self, filenames, pkg_name):
        self.pkg_name = pkg_name
        self.sources = {}
        for rel_fn, file_path in filenames.items():
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
                if fn and fn[0] == '$':
                    continue
                if fn in self.sources:
                    self.sources[fn].tags.add(tag)
                else:
                    print('    File %s found in CMake not found in folder!' % fn)

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

    def search_for_patterns(self, patterns, per_line=True):
        files = {}
        for source in self.sources.values():
            if per_line:
                matches = source.search_lines_for_patterns(patterns)
            else:
                matches = source.search_for_patterns(patterns)
            if len(matches) != 0:
                files[source.rel_fn] = matches
        return files

    def search_for_pattern(self, pattern, per_line=True):
        return self.search_for_patterns([pattern], per_line)

    def modify_with_patterns(self, patterns, language='c++', verbose=True):
        """
        Given a map of patterns, replace all instances in the package source code with the given language.

        The key in the map is a regular expression string literal.
        If there are no groups, then the matching string is replaced with the map value.
        If there are groups, then the literals of the form $0, $1, etc in the map value are replaced with the groups
        """
        for source in self.get_source_by_language(language):
            source.modify_with_patterns(patterns, verbose)

    def __repr__(self):
        return '\n'.join(map(str, sorted(self.sources.values())))
