#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tmux.py

Usage: tmux.py <server> <session> [options]

Options:
  --window-name=WINDOW_NAME
  -c --config=STRING        window configuration file [default: ~/.tmux/configs/default.yml]
  -d                        Start detached
  -k                        kill server
  -r                        remote server
  -l                        list sessions


"""
from docopt import docopt
import os
from os.path import expanduser, join
from tmuxp.workspacebuilder import WorkspaceBuilder
from libtmux.server import Server
from libtmux import exc
import platform
import logging
import yaml
import tempfile
import sys


logging.basicConfig(level=logging.INFO)


formatted_hostname = platform.node().split(".")[0].lower()
default_inner_cmd = ("python %s inner {name} ") % __file__


def gen_window_config(name, window_config):
    print("window config: %s" % window_config)
    return {
        "window_name": name,
        "panes": [
            {
                "shell_command": [
                    {
                        "cmd": window_config.get(
                            "shell_command",
                            default_inner_cmd.format(name=name),
                        )
                    }
                ],
                "start_directory": window_config.get("start_directory", "~/"),
            },
        ],
    }


def gen_session_config(name, config_map):
    return {
        "session_name": name,
        "windows": [
            gen_window_config(name, config)
            for name, config in config_map.get("windows", {}).items()
        ],
        "options": {"base-index": 0},
        "start_directory": config_map.get("start_directory", "~/"),
    }


def get_status_line(host_config, remote):
    status_left = (
        "#[fg={fg},bg={bg},bold] #S #[fg=colour238,bg=colour234,nobold]"
    )
    status_right = "#[fg={fg},bg={bg},bold] #h %H:%M:%S"
    bg = host_config.get("bg", "red") if remote else "green"
    fg = host_config.get("fg", "white") if remote else "black"
    status_left = status_left.format(
        bg=bg,
        fg=fg,
    )
    status_right = status_right.format(
        bg=bg,
        fg=fg,
    )
    return status_right, status_left


if __name__ == "__main__":
    args = docopt(__doc__)
    print(args)
    server_name = args["<server>"]
    session_name = args["<session>"]
    remote = args["-r"]  # or os.environ.get('SSH_TTY')
    kill = args["-k"]
    os.chdir(expanduser("~"))
    os.environ["PATH"] += os.pathsep + os.pathsep.join(
        ["~/.local/bin/", "/usr/local/bin/"]
    )

    host_config = {}
    for outer, inners in yaml.load(
        open(expanduser(args["--config"])), Loader=yaml.FullLoader
    )["windows"].items():
        host_config[outer] = gen_session_config(
            outer,
            inners,
        )

    session_config = host_config.get(
        session_name, gen_session_config(session_name, {})
    )
    windows = session_config["windows"]
    for i in range(10 - len(windows)):
        print(session_config)
        session_config["windows"].append(
            {
                "window_name": session_name,
                "start_directory": session_config.get("start_directory", "~/"),
                "panes": [{"shell_command": []}],
            }
        )

    server = Server(
        socket_path=join(tempfile.gettempdir(), "tmux_%s_socket" % server_name),
        # socket_name="tmux_%s_new" % server_name,
        config_file=expanduser("~/.tmux/%s.conf" % server_name),
    )

    builder = WorkspaceBuilder(sconf=session_config, server=server)
    session = None
    if args.get("-k"):
        try:
            session = server.find_where({"session_name": session_name})
            session.kill_session()
        except Exception as e:
            logging.exception("Error killing session")
            pass
        sys.exit(0)
    if args.get("-l"):
        print(server.list_sessions())
        sys.exit(0)
    try:
        logging.debug("Creating new Session ...")
        session = server.new_session(
            session_name=session_name,
            start_directory=session_config.get("start_directory", "~/"),
        )
        logging.debug("Done Creating new Session.")
    except exc.TmuxSessionExists:
        logging.debug("Session exists")
    try:
        builder.build(session)
    except exc.TmuxSessionExists:
        logging.debug("builder session exists")
        session = (
            session
            or builder.session
            or server.findWhere({"session_name": session_name})
        )

    builder = WorkspaceBuilder(sconf=session_config, server=server)
    sessions = None
    if not session:
        try:
            sessions = server.list_sessions()
            session = [s for s in sessions if s["session_name"] == session_name]
            session = session[0] if session else session
        except exc.TmuxpException:
            pass
    if not session:
        session = server.new_session(
            session_name=session_name,
            kill_session=True,
            start_directory=session_config.get("start_directory", "~/"),
        )
        builder.build(session)

    # if server_name == "outer":
    #    session.set_option("status-position", "top")
    # else:
    #    session.set_option("status-position", "bottom")

    if not args["-d"]:
        server.cmd("detach-client", "-s", session_name)

    status_right, status_left = get_status_line(host_config, remote)
    # for session in sessions:
    try:
        session.set_option("status-right", status_right)
        session.set_option("status-left", status_left)
        session.set_environment(
            "SSH_AUTH_SOCK", os.environ.get("SSH_AUTH_SOCK")
        )
        session.set_environment(
            "SSH_AGENT_PID", os.environ.get("SSH_AGENT_PID")
        )
        if not remote:
            session.cmd("set-environment", "-gu", "SSH_HOST_STR")
            session.cmd("set-environment", "-gu", "SSH_TTY_SET")
        session.cmd("set_option", "-g", "allow-rename", "on")
        session.cmd("set_option", "-g", "automatic-rename", "on")
    except Exception:
        logging.exception("error setting up session")

    if not args["-d"]:
        if "TMUX" in os.environ and "outer" in str(os.environ["TMUX"]):
            os.system("tmux rename-window %s" % session_name)
        server.attach_session(session_name)
