import re
import sys
from cmake import Command, Section, SectionStyle
ALL_CAPS = re.compile('^[A-Z_]+$')

def word_cb(scanner, token):
    if ALL_CAPS.match(token):
        return ('caps', token)
    else:
        return ('word', token)

scanner = re.Scanner([
    (r'#.*', lambda scanner, token: ("comment", token)),
    (r'"[^"]*"', lambda scanner, token: ("string", token)),
    (r"\(", lambda scanner, token: ("left paren", token)),
    (r"\)", lambda scanner, token: ("right paren", token)),
    (r'[^ \t\r\n()#"]+', word_cb),
    (r'\n', lambda scanner, token: ("newline", token)),
    (r"[ \t]+", lambda scanner, token: ("whitespace", token)),
])

ALL_WHITESPACE = ['whitespace', 'newline']
NOT_REAL = ALL_WHITESPACE + ['comment']

class AwesomeParser:
    def __init__(self, s, debug=False):
        self.tokens, remainder = scanner.scan(s)
        if remainder != '':
            msg = 'Unrecognized tokens: %s' % (remainder)
            raise ValueError(msg)

        if debug:
            for typ, token in self.tokens:
                print '[%s]%s' % (typ, repr(token))

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
        if debug:
            for chunk in self.contents:
                print '[%s]' % chunk

    def parse_command(self):
        command_name = self.match()
        original = command_name
        cmd = Command(command_name)
        while self.get_type() == 'whitespace':
            s = self.match('whitespace')
            cmd.pre_paren += s
            original += s
        original += self.match('left paren')

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
                    cmd.original = original
                    return cmd
                elif typ == 'left paren':
                    pass
                else:
                    cmd.sections.append(tok_contents)
        msg = 'File ended while processing command "%s"' % (command_name)
        raise CMakeParseError(msg)

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
        while self.next_real_type() not in ['right paren', 'caps']:
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
                # print delims
                style.val_sep = list(delims)[0]

        # print cat, tokens, style
        return Section(cat, tokens, style), original

    def match(self, typ=None):
        if typ is None or self.get_type() == typ:
            typ, tok = self.tokens.pop(0)
            # print '[%s]%s'%(typ, repr(tok))
            return tok
        else:
            sys.stderr.write('Expected type "%s" but got "%s"\n' % (typ, self.get_type()))
            for a in self.tokens:
                sys.stderr.write(str(a) + '\n')
            exit(-1)

    def get_type(self):
        if len(self.tokens) > 0:
            return self.tokens[0][0]
        else:
            return None

    def next_real_type(self):
        for x, y in self.tokens:
            if x not in NOT_REAL:
                return x

def parse_file(s):
    parser = AwesomeParser(s)
    return parser.contents

def parse_command(s):
    parser = AwesomeParser(s)
    assert len(parser.contents) == 1
    return parser.contents[0]
