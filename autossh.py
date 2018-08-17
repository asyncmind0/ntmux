#!/usr/bin/python
"""
Usage: autossh.py [options] <hostname> [<server> <sessionname>]

Options:
  -i FILE --identity FILE

"""
import signal
import os
from os.path import isfile
from docopt import docopt
from plumbum import FG
from plumbum.cmd import tmux, ssh
import shlex


def optparsing():
    args = docopt(__doc__)
    args['identity'] = args.get('--identity')
    hostname = args.get('<hostname>', 'autossh')
    port = None
    if ':' in hostname:
        hostname, port = hostname.split(':', 1)
    args['hostname'] = hostname
    args['port'] = port
    args['<sessionname>'] = args['<sessionname>'] or hostname.split('.', 1)[0]
    args['<server>'] = args['<server>'] or 'inner'
    print(args)
    return args

def deploy(args):
    ssh[
        args['hostname'],
        'git clone https://jagguli@bitbucket.org/jagguli/dottmux.git ~/.tmux' % args
    ] & FG((0, 128))
    ssh[
        args['hostname'],
        'tmux -V'
    ] & FG
    ssh[
        args['hostname'],
        'cd ~/.tmux; sh setup.sh'
    ] & FG


def attach_tmux(args):
    has_tmux = os.environ.get('TMUX')
    prev_window_name = None
    if has_tmux:
        prev_window_name = tmux("display-message", "-p", "x'#W")
        tmux("rename-window", args['hostname'])
    cmd = []
    cmd.extend(
        [
            "autossh",
            args['hostname'],
            "-M", "0",
            "-o",
            "ServerAliveInterval=10",
            "ServerAliveCountMax=5",
        ]
    )
    if args['port']:
        cmd.extend(('-p', args['port']))
    cmd.extend((
        "-t", "exec tmuxpy -r {<server>} {<sessionname>}".format(
            **args)))

    if args['identity']:
        cmd.extend(['-i', args['identity']])

    pid_file = "/tmp/autossh_%(<server>)s_%(<sessionname>)s.pid" % args
    os.environ['AUTOSSH_PIDFILE'] = pid_file
    os.environ['SSH_AUTH_SOCK'] = "/run/user/1000/gnupg/S.gpg-agent.ssh"
    os.environ["PATH"] += os.pathsep + os.pathsep.join(
        [
            "~/.local/bin/",
        ]
    )
    if isfile(pid_file):
        with open(pid_file) as pidf:
            try:
                os.kill(int(pidf.read()), signal.SIGINT)
                os.kill(int(pidf.read()), signal.SIGKILL)
            except Exception as e:
                os.unlink(pid_file)

    os.execvpe(cmd[0], cmd, dict(os.environ))

if __name__ == '__main__':
    #deploy(optparsing())
    attach_tmux(optparsing())
