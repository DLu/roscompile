import subprocess

PACKAGES = {}

p = subprocess.Popen(['rospack', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = p.communicate()

for line in out.split('\n'):
    if len(line.strip())==0:
        continue
    pkg, folder = line.split()
    PACKAGES[pkg] = folder
    
def is_package(pkg):
    return pkg in PACKAGES    
