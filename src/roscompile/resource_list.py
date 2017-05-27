import subprocess

def get_output_lines(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return [s for s in out.split('\n') if len(s) > 0]

PACKAGES = {}
MESSAGES = set()
SERVICES = set()

for line in get_output_lines(['rospack', 'list']):
    pkg, folder = line.split()
    PACKAGES[pkg] = folder

for line in get_output_lines(['rosmsg', 'list']):
    pkg, msg = line.split('/')
    MESSAGES.add((pkg, msg))

for line in get_output_lines(['rossrv', 'list']):
    pkg, srv = line.split('/')
    SERVICES.add((pkg, srv))

def is_package(pkg):
    return pkg in PACKAGES

def is_message(pkg, msg):
    return (pkg, msg) in MESSAGES

def is_service(pkg, srv):
    return (pkg, srv) in SERVICES
