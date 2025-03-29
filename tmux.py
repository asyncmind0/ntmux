#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tmux.py

Usage: tmux.py <server> <session> [options]

Options:
  -w --windows-config=STRING        window configuration file [default: ~/.tmux/configs/default.yml]
  -c --tmux-config=STRING        tmux configuration file [default: ~/.tmux/inner.conf]
  -d                        Start detached
  -k                        kill server
  -r                        remote server
  -l                        list sessions


"""
from docopt import docopt
import os
from os.path import expanduser, join, exists, basename
from tmuxp.workspace.builder import WorkspaceBuilder
from libtmux.server import Server
from libtmux import exc
import platform
import logging
import yaml
import tempfile
import sys

logging.basicConfig(level=logging.INFO)


formatted_hostname = platform.node().split(".")[0].lower()
default_inner_cmd = (
    "python %s inner -w ~/.tmux/configs/default.yml {name} "
) % __file__
FROZEN = getattr(sys, "frozen", False)


def get_env():
    env = dict(os.environ)  # make a copy of the environment
    lp_key = "LD_LIBRARY_PATH"  # for Linux and *BSD.
    lp_orig = env.get(lp_key + "_ORIG")  # pyinstaller >= 20160820 has this
    if lp_orig is not None:
        env[lp_key] = lp_orig  # restore the original, unmodified value
    else:
        env.pop(lp_key, None)  # last resort: remove the env var
    return env


def gen_window_config(name, window_config):
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


def get_config(conf_file):
    config_locations = [
        expanduser(conf_file),
        expanduser("~/.tmux/%s" % basename(conf_file)),
        expanduser("~/.tmuxpy/%s" % basename(conf_file)),
        expanduser("~/.local/etc/tmuxpy/%s" % basename(conf_file)),
        "/usr/local/etc/tmuxpy/%s" % basename(conf_file),
        "/etc/tmuxpy/%s" % basename(conf_file),
    ]
    for conf in config_locations:
        if exists(conf):
            logging.debug(f"using config {conf}")
            return conf
    raise Exception(
        """No %s config found!!
Please set config in one of these locations:
%s"""
        % (conf_file, "\n".join(config_locations))
    )


def main():
    if FROZEN:
        os.environ["LD_LIBRARY_PATH"] = os.environ.get(
            "LD_LIBRARY_PATH_ORIG", ""
        )
    args = docopt(__doc__)
    logging.debug(args)
    server_name = args["<server>"]
    session_name = args["<session>"]
    remote = args["-r"]  # or os.environ.get('SSH_TTY')
    os.chdir(expanduser("~"))
    os.environ["PATH"] += os.pathsep + os.pathsep.join(
        ["~/.local/bin/", "/usr/local/bin/"]
    )

    host_config = {}
    for outer, inners in yaml.safe_load(
        open(get_config(args["--windows-config"]))
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
        logging.debug(session_config)
        session_config["windows"].append(
            {
                "window_name": session_name,
                "start_directory": session_config.get("start_directory", "~/"),
                "panes": [
                    {
                        "shell_command": [
                            {
                                "cmd": session_config.get(
                                    "shell_command",
                                    default_inner_cmd.format(name=session_name),
                                )
                            }
                        ]
                        if "shell_command" in session_config
                        else [],
                    }
                ],
            }
        )

    server = Server(
        socket_path=join(tempfile.gettempdir(), "tmux_%s_socket" % server_name),
        # socket_name="tmux_%s_new" % server_name,
        config_file=get_config("%s.conf" % server_name),
    )
    builder = WorkspaceBuilder(sconf=session_config, server=server)
    session = None
    if args.get("-k"):
        try:
            session = server.find_where({"session_name": session_name})
            logging.info(f"Killing session {session_name}")
            if session:
                session.kill_session()
        except Exception as e:
            logging.exception("Error killing session")
            pass
        sys.exit(0)
    if args.get("-l"):
        logging.debug(server.list_sessions())
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
        # session = server.new_session(
        #    session_name=session_name,
        #    kill_session=True,
        #    start_directory=session_config.get("start_directory", "~/"),
        # )
        # builder.build(session)
        os.execvpe(
            "/usr/sbin/tmux",
            [
                f"-f{get_config('%s.conf' % server_name)}",
                f"-S{join(tempfile.gettempdir(), 'tmux_%s_socket' % server_name)}",
                "new-session",
                f"-t{session_name}",
                "-d",
            ],
            os.environ,
        )

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
        # session.cmd("set_option", "-g", "allow-rename", "on")
        session.cmd("set_option", "-g", "automatic-rename", "on")
    except Exception:
        logging.exception("error setting up session")

    if not args["-d"]:
        os.execvpe(
            "/usr/sbin/tmux",
            [
                f"-f{get_config('%s.conf' % server_name)}",
                f"-S{join(tempfile.gettempdir(), 'tmux_%s_socket' % server_name)}",
                "attach-session",
                f"-t{session_name}",
            ],
            os.environ,
        )
        # server.attach_session(session_name)

if __name__ == "__main__":
    main()
    logging.info("Tmuxpy done.")
