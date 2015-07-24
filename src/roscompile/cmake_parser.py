import sys
import re
from roscompile.cmake import *
ALL_CAPS = re.compile('^[A-Z_]+$')

class CommandScanner(re.Scanner):
    def __init__(self):
        re.Scanner.__init__(self, [
            (r'\w+ ?\(', CommandScanner.c_command),
            (r'\n', CommandScanner.c_nl),
            (r'[ \t]+', CommandScanner.c_ws),
            (r'[\w\.\$\{\}/\-:"\*,>=]+', CommandScanner.c_token),
            (r'#[^\n]*\n', CommandScanner.c_comment),
            (r'\)', None)
        ])

    def c_command(self, token): return ('name', token.replace(' ', ''))
    def c_nl(self, token): return ('nl', token)
    def c_ws(self, token): return ('white', token)
    def c_token(self, token):
        if ALL_CAPS.match(token):
            return ('caps', token)
        else:
            return ('token', token)
    def c_comment(self, token): return ('comment', token)
    
    def parse(self, s):
        contents,extra = self.scan(s)
        
        if len(extra)>0:
            sys.stderr.write('Could not parse command %s. Please report the error.\n'%s)
            sys.stderr.write(extra + '\n')
            exit(-1)
            
           
        self.tokens = contents
        
        cmd = Command(self._match('name')[:-1])
        cmd.add(self.parse_section(False))
        
        while self.next_real_type()=='caps':
            cmd.add(self.parse_section())
                    
        for x in self.tokens:
            if x[0]=='nl' or x[0]=='white':
                continue
            sys.stderr.write('Could not parse CMake properly. Please report the error.\n')
            sys.stderr.write(s + '\n')
            exit(-1)
        
        return cmd
        
    def parse_section(self, caps_required=True):
        cat = ''
        inline = True
        w = None
        pre = ''
        while self.get_type() == 'nl' or self.get_type()=='white':
            pre += self._match()
            
        if self.get_type()=='caps':
            cat = self._match('caps')
        elif caps_required:
            print 'Error'
            
        t, tab = self.parse_tokens()
        
        return Section(cat, t, pre, tab)
        
        
    def parse_tokens(self):
        tokens = []

        tab = None
        
        while self.get_type()=='comment':
            tokens.append( self._match('comment') )

        while self.next_real_type()=='token':
            while self.get_type() == 'nl' or self.get_type()=='white':
                if len(tokens)<2 :
                    if self.get_type()=='nl':
                        tab = 0
                        self._match()
                    elif self.get_type()=='white' and tab == 0:
                        ws = self._match().replace('\t', '    ')                        
                        tab = len( ws )
                    else:
                        self._match()
                else:
                    self._match()
            tokens.append( self._match('token') )
        return tokens, tab
        
    def get_type(self, peek=False):
        if peek:
            i = 1
        else:
            i = 0
        if len(self.tokens)>i:
            return self.tokens[i][0]
        else:
            return None
            
    def next_real_type(self):
        for x,y in self.tokens:
            if x!='white' and x!='nl' and x!='comment':
                return x
                
        
    def _match(self, tipo=None):
        if tipo is None or self.get_type() == tipo:
            tok = self.tokens[0][1]
            self.tokens.pop(0)
            return tok
        else:
            sys.stderr.write('Expected type "%s" but got "%s"\n'%(tipo, self.get_type()))
            for a in self.tokens:
                sys.stderr.write(str(a) + '\n')
            exit(-1)
            

c_scanner = CommandScanner()

class CMakeScanner(re.Scanner):
    def __init__(self):
        re.Scanner.__init__(self, [
     (r'\w+ ?\([^\)]*\)', CMakeScanner.s_command),
     (r'((#[^\n]*\n)*\s*)*', CMakeScanner.s_comment),
     ])
     
    def s_command(self, token): return c_scanner.parse(token)
        
        
    def s_comment(self, token): return token
    
    def parse(self, filename):
        s = open(filename).read()
        contents, extra = self.scan(s)
        if len(extra)>0:
            sys.stderr.write('Could not parse %s. Please report the error.\n'%filename)
            sys.stderr.write(extra + '\n')
            exit(-1)
        return contents    

scanner = CMakeScanner()
