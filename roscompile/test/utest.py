#!/usr/bin/env python
import inspect
from catkin.find_in_workspaces import find_in_workspaces
from ros_introspection.package import Package
from roscompile import get_functions
from roscompile.diff import prepare_diff_lines
from roscompile.zipfile_interface import get_use_cases_from_zip
import os.path

FILE_ERROR_MESSAGE = 'These files should have been {} but weren\'t: {}'

zipfile = find_in_workspaces(path='roscompile/test/test_data.zip', first_match_only=True)[0]
config, cases = get_use_cases_from_zip(zipfile)
roscompile_functions = get_functions()


def test_generator():
    for test_config in config:
        yield roscompile_check, test_config['in'], test_config['out'], \
            test_config['functions'], test_config.get('subpkg', None), test_config.get('config', {})


def roscompile_check(input_package, output_package, list_o_functions, subpkg=None, local_config=None):
    with cases[input_package] as pkg_in:
        pkg_out = cases[output_package]

        root = pkg_in.root
        if subpkg:
            root = os.path.join(root, subpkg)
        pp = Package(root)
        for function_name in list_o_functions:
            fne = roscompile_functions[function_name]
            if 'config' in inspect.getargspec(fne).args:
                fne(pp, config=local_config)
            else:
                fne(pp)
        pp.write()

        matches, missed_deletes, missed_gens = pkg_in.compare_filesets(pkg_out)
        assert len(missed_deletes) == 0, FILE_ERROR_MESSAGE.format('deleted', str(missed_deletes))
        assert len(missed_gens) == 0, FILE_ERROR_MESSAGE.format('generated', str(missed_gens))
        for filename in matches:
            generated_contents = pkg_in.get_contents(filename).strip()
            canonical_contents = pkg_out.get_contents(filename).strip()
            if generated_contents != canonical_contents:
                for gen_line, can_line in prepare_diff_lines(generated_contents, canonical_contents):
                    if gen_line != can_line:
                        print(repr(gen_line) + ' should be ' + repr(can_line))

            assert generated_contents == canonical_contents, 'The contents of {} do not match!'.format(filename)
