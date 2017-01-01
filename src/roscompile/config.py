import os.path
import yaml

FILENAME = os.path.expanduser('~/.ros/roscompile.yaml')

class Config(dict):
    def __init__(self):
        if os.path.exists(FILENAME):
            self.update( yaml.load( open( FILENAME ) ) )
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

    def should(self, verb):
        if verb not in self['flags']:
            self['flags'][verb] = False
        return self['flags'][verb]

    def write(self):
        yaml.dump(dict(self), open(FILENAME, 'w'), default_flow_style=False)

CFG = Config()
