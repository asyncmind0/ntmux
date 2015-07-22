#!/usr/bin/python
"""
Usage: autossh.py <hostname> [<server> <sessionname>]

"""
import os
from docopt import docopt
from sh import tmux

args = docopt(__doc__)
hostname = args.get('<hostname>', 'autossh')
port = None
if ':' in hostname:
    hostname, port = hostname.split(':', 1)
args['<sessionname>'] = args['<sessionname>'] or hostname.split('.', 1)[0]
args['<server>'] = args['<server>'] or 'inner'
print(args)

has_tmux = os.environ.get('TMUX')
prev_window_name = None
if has_tmux:
    prev_window_name = tmux("display-message", "-p", "x'#W")
    tmux("rename-window", hostname)

cmd = ["autossh", hostname, "-M", "0"]
if port:
    cmd.extend(('-p', port))
cmd.extend(("-t", "~/.bin/tmux.py {<server>} {<sessionname>}".format(**args)))
print(cmd)
os.execvpe("/usr/bin/autossh", cmd, os.environ)
