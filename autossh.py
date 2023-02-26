#!/usr/bin/env python
"""
Usage: autossh.py [options] <hostname> [<server> <sessionname>]

Options:
  -i FILE --identity FILE
  -b --binary-build

"""
import signal
import os
from os.path import isfile, join
from docopt import docopt
import subprocess
import tempfile


def get_env():
    env = dict(os.environ)  # make a copy of the environment
    lp_key = "LD_LIBRARY_PATH"  # for Linux and *BSD.
    lp_orig = env.get(lp_key + "_ORIG")  # pyinstaller >= 20160820 has this
    if lp_orig is not None:
        env[lp_key] = lp_orig  # restore the original, unmodified value
    else:
        env.pop(lp_key, None)  # last resort: remove the env var
    return env


def optparsing():
    args = docopt(__doc__)
    args["identity"] = args.get("--identity")
    args["binary"] = args.get("--binary-build")
    hostname = args.get("<hostname>", "autossh")
    port = None
    if ":" in hostname:
        hostname, port = hostname.split(":", 1)
    args["hostname"] = hostname
    args["port"] = port
    args["<sessionname>"] = args["<sessionname>"] or hostname.split(".", 1)[0]
    args["<server>"] = args["<server>"] or "inner"
    print(args)
    return args


def deploy(args):
    ssh[
        args["hostname"],
        "git clone https://jagguli@bitbucket.org/jagguli/dottmux.git ~/.tmux"
        % args,
    ] & FG((0, 128))
    ssh[args["hostname"], "tmux -V"] & FG
    ssh[args["hostname"], "cd ~/.tmux; sh setup.sh"] & FG


def attach_tmux(args):
    has_tmux = os.environ.get("TMUX")
    prev_window_name = None
    if has_tmux:
        prev_window_name = subprocess.check_output(
            ["tmux", "display-message", "-p", "x'#W"], env=get_env()
        )
        subprocess.check_call(
            ["tmux", "rename-window", args["hostname"]], env=get_env()
        )
    cmd = []
    cmd.extend(
        [
            "autossh",
            "-M",
            "0",
            "-t",
            args["hostname"],
            "-o",
            "ServerAliveInterval=10",
            "-o",
            "ServerAliveCountMax=5",
        ]
    )
    if args["port"]:
        cmd.extend(("-p", args["port"]))
    if args["binary"]:

        cmd.append("exec tmuxpy -r {<server>} {<sessionname>}".format(**args))
    else:
        cmd.append(
            "PATH=$PATH:~/.local/bin/ exec tmux.py -r {<server>} {<sessionname>}".format(
                **args
            )
        )

    if args["identity"]:
        cmd.extend(["-i", args["identity"]])

    pid_file = join(
        tempfile.gettempdir(),
        "autossh_%(<server>)s_%(<sessionname>)s.pid" % args,
    )
    os.environ["AUTOSSH_PIDFILE"] = pid_file
    # os.environ["SSH_AUTH_SOCK"] = "/run/user/1000/gnupg/S.gpg-agent.ssh"
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

    os.execvpe(cmd[0], cmd, get_env())


if __name__ == "__main__":
    # deploy(optparsing())
    attach_tmux(optparsing())
