import argparse
import inspect
from zipfile_interface import get_test_cases
from ros_introspection.package import Package
from roscompile import get_functions
import os.path


def compare(pkg_in, pkg_out, debug=True):
    matches, missed_deletes, missed_generations = pkg_in.compare_filesets(pkg_out)

    success = True

    for fn in missed_deletes:
        if debug:
            print 'Should have deleted %s' % fn
        success = False
    for fn in missed_generations:
        if debug:
            print 'Failed to generate %s' % fn
        success = False
    for filename in matches:
        generated_contents = pkg_in.get_contents(filename)
        canonical_contents = pkg_out.get_contents(filename)
        if generated_contents.strip() == canonical_contents.strip():
            continue
        success = False
        if debug:
            A = generated_contents.split('\n')
            B = canonical_contents.split('\n')
            while len(A) < len(B):
                A.append(None)
            while len(B) < len(A):
                B.append(None)
            for a, b in zip(A, B):
                print a == b, repr(a), repr(b)
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

                print '{:25} >> {:25} {}'.format(test_config['in'], test_config['out'],
                                                 ','.join(test_config['functions']))
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
                    print '  SUCCESS'
                    successes += 1
                else:
                    print '  FAIL'
                    if args.fail_once:
                        break
            except Exception as e:
                print '  EXCEPTION', e.message
                if args.last:
                    raise
                if args.fail_once:
                    break
    if not args.last:
        print '{}/{}'.format(successes, total)
