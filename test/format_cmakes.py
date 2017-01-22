#!/usr/bin/python
import argparse
import difflib
from roscompile.cmake import CMake

def diff(a, b):
    diff = difflib.unified_diff(str(a).split('\n'), str(b).split('\n'))
    print '\n'.join(diff)

parser = argparse.ArgumentParser()
parser.add_argument('inputs', metavar='input', nargs='+')
args = parser.parse_args()

for fn in args.inputs:
    print '='*10, fn, '='*40
    original = open(fn).read()
    cmake = CMake(fn)
    diff(original, cmake)
    #print original
    #print 'x'*50
    #print str(cmake)

