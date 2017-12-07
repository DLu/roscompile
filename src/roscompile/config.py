import os.path
import yaml
import argparse

FILENAME = os.path.expanduser('~/.ros/roscompile.yaml')

class Config(dict):
    def __init__(self):
        if os.path.exists(FILENAME):
            self.update(yaml.load(open(FILENAME)))
            if 'flags' not in self:
                keys = set()
                flags = {}
                for key in self:
                    if key == 'canonical_names':
                        continue
                    flags[key] = self[key]
                    keys.add(key)
                for key in keys:
                    del self[key]
                self['flags'] = flags
        else:
            self['flags'] = {}

        self.args = {}

    def check_command_flags(self):
        parser = get_parser_with_flags()
        self.args = parser.parse_args()

    def should(self, verb):
        if verb not in self['flags']:
            self['flags'][verb] = False
        return self['flags'][verb] or (hasattr(self.args, verb) and getattr(self.args, verb))

    def write(self):
        yaml.dump(dict(self), open(FILENAME, 'w'), default_flow_style=False)

CFG = Config()

def get_parser_with_flags():
    parser = argparse.ArgumentParser(description='Tool for fixing up your ros code. '
                                                 'Most options start False by default,'
                                                 ' unless they are flipped in %s' % FILENAME)
    for name, value in sorted(CFG.items()):
        action = 'store_true' if not value else 'store_false'
        parser.add_argument('--' + name, action=action, help='(disable)' if value else '')
    return parser
