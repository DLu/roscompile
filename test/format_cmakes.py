#!/usr/bin/python
import argparse
import difflib
import traceback
from roscompile.cmake import CMake

def diff(a, b, quit_if_diff=False):
    diff = list(difflib.unified_diff(str(a).split('\n'), str(b).split('\n')))
    print '\n'.join(diff)
    if len(diff)>0 and quit_if_diff:
        exit(0)

parser = argparse.ArgumentParser()
parser.add_argument('inputs', metavar='input', nargs='+')
parser.add_argument('-x', '--quit-after-error', action='store_true')
parser.add_argument('-d', '--quit-after-diff', action='store_true')
parser.add_argument('-r', '--regenerate', action='store_true')
args = parser.parse_args()

for fn in args.inputs:
    print '='*10, fn, '='*40
    original = open(fn).read()
    try:
        cmake = CMake(fn)
        if args.regenerate:
            for chunk in cmake.contents:
                if type(chunk)==str:
                    continue
                chunk.changed = True
        s = str(cmake)
        diff(original, s, args.quit_after_diff)
    except Exception as e:
        print 'Failed parsing!'
        print e
        print traceback.print_exc()
        if args.quit_after_error:
            break

