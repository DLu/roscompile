import os.path
import yaml

FILENAME = os.path.expanduser('~/.ros/roscompile.yaml')

class Config(dict):
    def __init__(self):
        if os.path.exists(FILENAME):
            self.update( yaml.load( open( FILENAME ) ) )

    def should(self, verb):
        if verb not in self:
            self[verb] = True
        return self[verb]

    def write(self):
        yaml.dump(dict(self), open(FILENAME, 'w'), default_flow_style=False)

CFG = Config()
