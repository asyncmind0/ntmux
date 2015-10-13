#!/usr/bin/python
"""
Usage: autossh.py <hostname> [<server> <sessionname>]

"""
import signal
import os
from os.path import isfile
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

cmd = ["/usr/sbin/envoy-exec", "/bin/autossh", hostname, "-M", "0",
       "-o", "ServerAliveInterval=10", "ServerAliveCountMax=5"]
if port:
    cmd.extend(('-p', port))
cmd.extend(("-t", "~/.local/bin/tmux.py {<server>} {<sessionname>}".format(
    **args)))

pid_file = "/tmp/autossh_%s.pid" % hostname
os.environ['AUTOSSH_PIDFILE'] = pid_file
if isfile(pid_file):
    with open(pid_file) as pidf:
        os.kill(int(pidf.read()), signal.SIGINT)

os.execvpe(cmd[0], cmd, dict(os.environ))
