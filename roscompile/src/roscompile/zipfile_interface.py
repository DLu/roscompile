import os
import yaml
import shutil
import zipfile
import tempfile
import collections
from roscompile.util import make_executable


class ROSCompilePackageFiles:
    def __init__(self, package_name, pkg_files, executables):
        self.package_name = package_name
        self.is_written = False
        self.root = self.get_input_root()
        self.pkg_files = pkg_files
        self.executables = executables

    def copy(self):
        return ROSCompilePackageFiles(self.package_name, self.pkg_files, self.executables)

    def get_input_root(self):
        return os.path.join(tempfile.gettempdir(), self.package_name)

    def __enter__(self):
        self.write()
        self.is_written = True
        return self

    def __exit__(self, type, value, traceback):
        self.is_written = False
        self.clear()

    def get_filenames(self):
        if self.is_written:
            the_files = []
            for folder, _, files in os.walk(self.root):
                short_folder = folder.replace(self.root, '')
                if len(short_folder) > 0 and short_folder[0] == '/':
                    short_folder = short_folder[1:]
                for fn in files:
                    the_files.append(os.path.join(short_folder, fn))
            return set(the_files)
        else:
            return set(self.pkg_files.keys())

    def get_contents(self, filename):
        if self.is_written:
            full_path = os.path.join(self.root, filename)
            if os.path.exists(full_path):
                return open(full_path).read().replace('\r\n', '\n')
        elif filename in self.pkg_files:
            return self.pkg_files[filename].replace('\r\n', '\n')

    def compare_filesets(self, other_package):
        in_keys = self.get_filenames()
        out_keys = other_package.get_filenames()
        matches = in_keys.intersection(out_keys)
        missed_deletes = in_keys - out_keys
        missed_generations = out_keys - in_keys
        return matches, missed_deletes, missed_generations

    def write(self):
        self.clear()
        os.mkdir(self.root)
        for fn, contents in self.pkg_files.items():
            outfile = os.path.join(self.root, fn)
            parts = outfile.split(os.sep)
            # Parts will be '', tmp, pkg_name, possible_folders, actual_filename
            # Create the possible_folders as needed
            for i in range(4, len(parts)):
                new_folder = os.sep.join(parts[:i])
                if not os.path.exists(new_folder):
                    os.mkdir(new_folder)
            with open(outfile, 'w') as f:
                f.write(contents)
            if fn in self.executables:
                make_executable(outfile)

    def clear(self):
        if os.path.exists(self.root):
            shutil.rmtree(self.root)

    def __repr__(self):
        return self.package_name


def get_test_cases(zip_filename):
    file_data = collections.defaultdict(dict)
    zf = zipfile.ZipFile(zip_filename)
    config = None
    executables = set()
    for file in zf.filelist:
        if file.filename[-1] == '/':
            continue
        if file.filename == 'list_o_tests.yaml':
            config = yaml.safe_load(zf.read(file))
            continue
        parts = file.filename.split(os.path.sep)
        package = parts[0]
        path = os.path.join(*parts[1:])
        file_data[package][path] = zf.read(file).decode()
        if (file.external_attr >> 16) & 0o111:
            executables.add(path)

    test_data = {}
    for package, D in file_data.items():
        test_data[package] = ROSCompilePackageFiles(package, D, executables)
    for D in config:
        if 'function' in D:
            D['functions'] = [D['function']]
            del D['function']
    return config, test_data


def get_use_cases_from_zip(zip_filename):
    """Alias to avoid having the word "test" in utest.py"""
    return get_test_cases(zip_filename)
