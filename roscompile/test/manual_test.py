import argparse
import inspect
import os.path

import click

from ros_introspection.package import Package
from roscompile import get_functions
from roscompile.diff import prepare_diff_lines
from roscompile.zipfile_interface import get_test_cases


def compare(pkg_in, pkg_out, debug=True):
    matches, missed_deletes, missed_generations = pkg_in.compare_filesets(pkg_out)

    success = True

    for fn in missed_deletes:
        if debug:
            click.secho('Should have deleted %s' % fn, fg='yellow')
        success = False
    for fn in missed_generations:
        if debug:
            click.secho('Failed to generate %s' % fn, fg='yellow')
        success = False
    for filename in matches:
        generated_contents = pkg_in.get_contents(filename).replace('\r\n', '\n')
        canonical_contents = pkg_out.get_contents(filename).replace('\r\n', '\n')
        if generated_contents.strip() == canonical_contents.strip():
            continue
        success = False
        if debug:
            for gen_line, can_line in prepare_diff_lines(generated_contents, canonical_contents):
                if gen_line == can_line:
                    click.echo(repr(gen_line))
                else:
                    click.secho(repr(gen_line) + ' should be ' + repr(can_line), fg='yellow')
    return success


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('zipfile')
    parser.add_argument('-f', '--fail_once', action='store_true')
    parser.add_argument('-l', '--last', action='store_true')
    args = parser.parse_args()
    config, cases = get_test_cases(args.zipfile)
    roscompile_functions = get_functions()
    successes = 0
    total = 0

    for test_config in config:
        if args.last and test_config != config[-1]:
            continue

        with cases[test_config['in']] as pkg_in:
            try:
                total += 1
                if test_config['in'] == test_config['out']:
                    pkg_out = pkg_in.copy()
                else:
                    pkg_out = cases[test_config['out']]

                click.secho('{:25} >> {:25} {}'.format(test_config['in'], test_config['out'],
                                                       ','.join(test_config['functions'])),
                            bold=True, fg='white')
                root = pkg_in.root
                if 'subpkg' in test_config:
                    root = os.path.join(root, test_config['subpkg'])
                pp = Package(root)
                local_config = test_config.get('config', {})
                for function_name in test_config['functions']:
                    fne = roscompile_functions[function_name]
                    if 'config' in inspect.getargspec(fne).args:
                        fne(pp, config=local_config)
                    else:
                        fne(pp)
                pp.write()
                if compare(pkg_in, pkg_out):
                    click.secho('  SUCCESS', fg='green')
                    successes += 1
                else:
                    click.secho('  FAIL', fg='red')
                    if args.fail_once:
                        break
            except Exception as e:
                click.secho('  EXCEPTION ' + str(e), fg='red')
                if args.last:
                    raise
                if args.fail_once:
                    break
    if not args.last:
        click.secho('{}/{}'.format(successes, total), bold=True, fg='white')
