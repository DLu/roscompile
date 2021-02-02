import os.path
import re
import sys

from .cmake import CMake, Command, CommandGroup, Section, SectionStyle

ALL_CAPS = re.compile('^[A-Z_]+$')
ALL_WHITESPACE = ['whitespace', 'newline']
NOT_REAL = ALL_WHITESPACE + ['comment']


def word_cb(scanner, token):
    if ALL_CAPS.match(token):
        return ('caps', token)
    else:
        return ('word', token)


scanner = re.Scanner([
    (r'#.*\n', lambda scanner, token: ('comment', token)),
    (r'"[^"]*"', lambda scanner, token: ('string', token)),
    (r'\(', lambda scanner, token: ('left paren', token)),
    (r'\)', lambda scanner, token: ('right paren', token)),
    (r'[^ \t\r\n()#"]+', word_cb),
    (r'\n', lambda scanner, token: ('newline', token)),
    (r'[ \t]+', lambda scanner, token: ('whitespace', token)),
])


def match_command_groups(contents, base_depth=0):
    revised_contents = []

    current = []
    group = None
    depth = base_depth

    for content in contents:
        if group is None:
            if content.__class__ == Command and content.command_name in ['if', 'foreach']:
                group = content
                depth = base_depth + 1
            else:
                revised_contents.append(content)
        else:
            if content.__class__ == Command:
                if content.command_name == group.command_name:
                    depth += 1
                elif content.command_name == 'end' + group.command_name:
                    depth -= 1
                    if depth == base_depth:
                        recursive_contents = match_command_groups(current, base_depth + 1)
                        sub = CMake(initial_contents=recursive_contents, depth=base_depth + 1)
                        cg = CommandGroup(group, sub, content)
                        revised_contents.append(cg)
                        group = None
                        current = []
                        continue
            current.append(content)

    # Only will happen if the tags don't match. Shouldn't happen, but resolve leftovers
    if len(current) > 0:
        revised_contents += current

    return revised_contents


class CMakeParseError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class AwesomeParser:
    def __init__(self, s, debug=False):
        self.tokens, remainder = scanner.scan(s)
        if remainder != '':
            msg = 'Unrecognized tokens: %s' % (remainder)
            raise ValueError(msg)

        if debug:
            for typ, token in self.tokens:
                print('[%s]%s' % (typ, repr(token)))

        self.contents = []
        while len(self.tokens) > 0:
            typ = self.get_type()
            if typ == 'comment':
                self.contents.append(self.match(typ))
            elif typ == 'newline' or typ == 'whitespace':
                s = self.match(typ)
                self.contents.append(s)
            elif typ in ['word', 'caps']:
                cmd = self.parse_command()
                self.contents.append(cmd)
            else:
                raise Exception('token ' + typ)

        # Match Command Groups
        self.contents = match_command_groups(self.contents)

        if debug:
            for chunk in self.contents:
                print('[%s]' % chunk)

    def parse_command(self):
        command_name = self.match()
        original = command_name
        cmd = Command(command_name)
        while self.get_type() == 'whitespace':
            s = self.match('whitespace')
            cmd.pre_paren += s
            original += s
        original += self.match('left paren')
        paren_depth = 1

        while len(self.tokens) > 0:
            typ = self.next_real_type()
            if typ in ['word', 'caps', 'string']:
                section, s = self.parse_section()
                cmd.sections.append(section)
                original += s
            else:
                typ, tok_contents = self.tokens.pop(0)
                original += tok_contents
                if typ == 'right paren':
                    paren_depth -= 1
                    if paren_depth == 0:
                        cmd.original = original
                        return cmd
                elif typ == 'left paren':
                    paren_depth += 1
                else:
                    cmd.sections.append(tok_contents)
        raise CMakeParseError('File ended while processing command "%s"' % (command_name))

    def parse_section(self):
        original = ''
        style = SectionStyle()
        tokens = []
        cat = ''
        while self.get_type() in NOT_REAL:
            s = self.match()
            original += s
            style.prename += s

        if self.get_type() == 'caps':
            cat = self.match('caps')
            original += cat
            style.name_val_sep = ''
            while self.get_type() in ALL_WHITESPACE:
                s = self.match()
                original += s
                style.name_val_sep += s
            if len(style.name_val_sep) == 0:
                style.name_val_sep = ' '

        delims = set()
        current = ''
        while self.next_real_type() not in ['left paren', 'right paren', 'caps']:
            typ = self.get_type()
            if typ in ALL_WHITESPACE:
                token = self.match()
                original += token
                current += token
            else:
                if len(current) > 0:
                    delims.add(current)
                current = ''
                token = self.match()
                original += token
                tokens.append(token)
        if len(current) > 0:
            delims.add(current)
        if len(delims) > 0:
            if len(delims) == 1:
                style.val_sep = list(delims)[0]
            else:
                # TODO: Smarter multi delim parsing
                # print(delims)
                style.val_sep = list(delims)[0]

        # print(cat, tokens, style)
        return Section(cat, tokens, style), original

    def match(self, typ=None):
        if typ is None or self.get_type() == typ:
            typ, tok = self.tokens.pop(0)
            # print('[%s]%s'%(typ, repr(tok)))
            return tok
        else:
            sys.stderr.write('Token Dump:\n')
            for a in self.tokens:
                sys.stderr.write(str(a) + '\n')
            raise CMakeParseError('Expected type "%s" but got "%s"' % (typ, self.get_type()))

    def get_type(self):
        if len(self.tokens) > 0:
            return self.tokens[0][0]
        else:
            return None

    def next_real_type(self):
        for x, y in self.tokens:
            if x not in NOT_REAL:
                return x


def parse_commands(s):
    parser = AwesomeParser(s)
    return parser.contents


def parse_command(s):
    parser = AwesomeParser(s)
    assert len(parser.contents) == 1
    return parser.contents[0]


def parse_file(filename):
    if not os.path.exists(filename):
        return
    with open(filename) as f:
        s = f.read()
        return CMake(file_path=filename, initial_contents=parse_commands(s))
