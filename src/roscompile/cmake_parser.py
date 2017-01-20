import re, sys
from cmake import Command, Section
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
    (r"\s+", lambda scanner, token: ("whitespace", token)),
])

ALL_WHITESPACE = ['whitespace', 'newline']
NOT_REAL = ALL_WHITESPACE + ['comment']

class AwesomeParser:
    def __init__(self, s):
        self.tokens, remainder = scanner.scan(s)
        if remainder != '':
            msg = 'Unrecognized tokens: %s' % (remainder)
            raise ValueError(msg)
            
        self.contents = []
        prev_type = 'newline'
        while len(self.tokens)>0:
            typ = self.get_type()
            if typ == 'comment':
                self.contents.append(self.match(typ))
            elif typ == 'newline':
                self.match(typ)
                if prev_type == 'newline':
                    self.contents.append('\n')
            elif typ in 'word':
                cmd = self.parse_command()
                self.contents.append(cmd)
            elif typ == 'whitespace':
                self.match(typ)
                continue
            else:
                print 'token', typ
                exit(0)
            prev_type = typ

    def parse_command(self):
        command_name = self.match('word')
        original = command_name
        while self.get_type()=='whitespace':
            original += self.match('whitespace')
        self.match('left paren')
        original = command_name + '('
        cmd = Command(command_name)
        while len(self.tokens)>0:
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
                elif typ in ALL_WHITESPACE:
                    continue
                elif typ == 'comment':
                    cmd.sections.append(tok_contents)
        msg = 'File ended while processing command "%s"' % (command_name)
        raise CMakeParseError(msg)

    def parse_section(self):
        original = ''
        pre = ''
        tokens = []
        cat = ''
        
        while self.get_type() in ALL_WHITESPACE:
            pre += self.match()
            
        if self.get_type() == 'caps':
            cat = self.match('caps')
        original += pre + cat
            
        tab = None
        
        while self.next_real_type() not in ['right paren', 'caps']:
            typ = self.get_type()
            if typ in ALL_WHITESPACE:
                token = self.match()
                original += token
                if len(tokens)<2:
                    if typ=='newline':
                        tab = 0
                    elif tab==0:
                        token = token.replace('\t', '    ')
                        tab = len(token)
            else:
                token = self.match()
                original += token
                tokens.append(token)

        while self.get_type() in NOT_REAL:
            typ, token = self.tokens.pop(0)
            original += token
            if typ == 'comment':
                tokens.append( token )
        return Section(cat, tokens, pre, tab), original

    def match(self, typ=None):
        if typ is None or self.get_type() == typ:
            tok = self.tokens[0][1]
            self.tokens.pop(0)
            return tok
        else:
            sys.stderr.write('Expected type "%s" but got "%s"\n'%(typ, self.get_type()))
            for a in self.tokens:
                sys.stderr.write(str(a) + '\n')
            exit(-1)

    def get_type(self):
        if len(self.tokens)>0:
            return self.tokens[0][0]
        else:
            return None
    
    def next_real_type(self):
        for x,y in self.tokens:
            if x not in NOT_REAL:
                return x

def parse_file(s):
    parser = AwesomeParser(s)
    return parser.contents
