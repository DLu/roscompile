from resource_retriever import get
import re
HASH_PATTERN = re.compile('\n#+\n')

def get_ignore_data_helper(basename):
    #try:
        fn = 'package://roscompile/data/' + basename + '.ignore'
        lines = []
        for s in get(fn).read().split('\n'):
            if len(s) > 0:
                lines.append(s + '\n')
        return lines
    #except:
    #    return []

def get_ignore_data(name):
    return get_ignore_data_helper(name), get_ignore_data_helper(name + '_patterns')

def clean_contents(s, name, variables=None):
    ignore_lines, ignore_patterns = get_ignore_data(name)
    for line in ignore_lines:
        s = s.replace(line, '')
    if not variables:
        return s
    for pattern in ignore_patterns:
        s = s.replace(pattern % variables, '')
    return s

def remove_blank_lines(s):
    while '\n\n\n' in s:
        s = s.replace('\n\n\n', '\n\n')
    return s

def remove_all_hashes(s):
    m = HASH_PATTERN.search(s)
    while m:
        s = s.replace(m.group(0), '\n')
        m = HASH_PATTERN.search(s)
    return s

def simplify(s):
    try:
        return str(s)
    except:
        return s
