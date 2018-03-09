import subprocess
try:
    from colorama import Fore, Back, init
    init()
except ImportError:  # fallback so that the imported classes always exist
    class ColorFallback():
        def __getattr__(self, name):
            return ''
    Fore = Back = ColorFallback()

rows, columns = map(int, subprocess.check_output(['stty', 'size']).split())


def color_diff(diff):
    for line in diff:
        if line.startswith('+'):
            yield Fore.GREEN + line + Fore.RESET
        elif line.startswith('-'):
            yield Fore.RED + line + Fore.RESET
        elif line.startswith('^'):
            yield Fore.BLUE + line + Fore.RESET
        else:
            yield line


def color_header(s, fore='WHITE', back='BLUE'):
    header = ''
    line = '+' + ('-' * (columns - 2)) + '+'
    header += getattr(Fore, fore) + getattr(Back, back) + line
    n = columns - len(s) - 3
    header += '| ' + s + ' ' * n + '|'
    header += line + Back.RESET + Fore.RESET
    return header


def color_text(s, fore='YELLOW'):
    return getattr(Fore, fore) + s + Fore.RESET


def query_yes_no(question, default="no"):
    """Ask a yes/no question via raw_input() and return their answer.

    Based on http://code.activestate.com/recipes/577058/

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        choice = raw_input(color_text(question + prompt)).lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').")
