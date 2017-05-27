import sys
import collections
from roscompile.config import CFG
from roscompile.util import simplify

def query(s):
    return simplify(raw_input(s).decode(sys.stdin.encoding))

def get_rule_match(replace_rules, name, email):
    for key in ((name, email), ('*', email), (name, '*')):
        if key in replace_rules:
            return replace_rules[key]

def fix_people(pkgs, interactive=True):
    people = collections.defaultdict(set)
    for package in pkgs:
        for tag, the_list in package.get_people().iteritems():
            for name, email in the_list:
                people[email].add(name)

    if 'canonical_names' not in CFG and interactive:
        name = query('What is your name (exactly as you\'d like to see it in the documentation)? ')
        email = query('What is your email (for documentation purposes)? ')

        CFG['canonical_names'] = [{'name': name, 'email': email}]
    canonical = []
    canonical_names = {}
    canonical_emails = {}
    for d in CFG['canonical_names']:
        name = d['name']
        email = d['email']
        canonical_names[name] = email
        canonical_emails[email] = name
        canonical.append((name, email))

    replace_rules = {}
    for d in CFG.get('replace_rules', []):
        from_key = d['from']['name'], d['from']['email']
        to_key = d['to']['name'], d['to']['email']
        replace_rules[from_key] = to_key

    for email, names in people.iteritems():
        if len(names) == 1:
            one_name = list(names)[0]
            matching_rule = get_rule_match(replace_rules, one_name, email)
            if matching_rule is not None:
                continue
            elif email in canonical_emails:
                if canonical_emails[email] == one_name:
                    continue
                else:
                    print 'The name "%s" found in the packages for %s does not match saved name "%s"' % \
                          (one_name, email, canonical_emails[email])
                    continue
            elif one_name in canonical_names:
                print 'The email "%s" found in the packages for %s does not match saved email "%s"' % \
                      (email, one_name, canonical_names[one_name])
                continue
            elif interactive:
                response = 'x'
                while response not in 'abcq':
                    print 'New person %s/%s found! What would you like to do? ' % (one_name, email)
                    print ' a) Leave it be.'
                    print ' b) Replace with another.'
                    print ' c) Mark as canonical name.'
                    print ' q) Quit.'
                    response = raw_input('? ').lower()
                if response == 'q':
                    exit(0)
                elif response == 'a':
                    continue
                elif response == 'b':
                    response = ''
                    new_name = None
                    new_email = None
                    options = canonical[:]
                    for email0, names0 in people.iteritems():
                        if email == email0:
                            continue
                        for name in names0:
                            key = (name, email0)
                            if key not in options:
                                options.append((name, email0))
                    while True:
                        print "== Options =="
                        for i, (name, email0) in enumerate(options):
                            print '%d) %s/%s' % (i, name, email0)
                        print 'n) None of the above'
                        print 'i) Nevermind.'
                        print 'q) Quit.'
                        response = raw_input('? ')
                        if response == 'q':
                            exit(0)
                        elif response == 'i':
                            continue
                        elif response == 'n':
                            new_name = query('New name? ')
                            new_email = query('New email? ')
                            break
                        try:
                            choice = int(response)
                            if choice >= 0 and choice < len(options):
                                new_name, new_email = options[choice]
                                break
                        except:
                            None
                    if new_name and new_email:
                        new_key = '%s/%s' % (new_name, new_email)
                        response = 'x'
                        while response not in 'abcdq':
                            print "== Should we always do this? =="
                            print ' a) Always replace exact match %s/%s with %s' % (one_name, email, new_key)
                            print ' b) Replace anyone with the name %s with %s' % (one_name, new_key)
                            print ' c) Replace anyone with the email %s with %s' % (email, new_key)
                            print ' d) Just do it for now.'
                            print ' q) Quit.'
                            response = raw_input('? ').lower()
                        if response == 'q':
                            exit(0)
                        if response == 'b':
                            email = '*'
                        elif response == 'c':
                            one_name = '*'
                        replace_rules[(one_name, email)] = (new_name, new_email)
                        if response in 'abc':
                            new_value = {}
                            new_value['from'] = {'email': simplify(email), 'name': simplify(one_name)}
                            new_value['to'] = {'email': simplify(new_email), 'name': simplify(new_name)}
                            if 'replace_rules' not in CFG:
                                CFG['replace_rules'] = []
                            CFG['replace_rules'].append(new_value)
                else:
                    canonical_names[one_name] = email
                    canonical_emails[email] = one_name
                    canonical.append((one_name, email))
                    if 'canonical_names' not in CFG:
                        CFG['canonical_names'] = []
                    CFG['canonical_names'].append({'name': one_name, 'email': email})
                    continue
        else:
            print 'Found %s with multiple names: %s' % (email, ', '.join(names))
    package.update_people(replace_rules)
