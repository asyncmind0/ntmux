#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tmux.py

Usage: tmux.py <server> <session> [options]

Options:
  --window-name=WINDOW_NAME
  -w --windows-config=STRING        window configuration file [default: windows.yml]
  -c --tmux-config=STRING        tmux configuration file [default: inner.conf]
  -d                        Start detached
  -k                        kill server
  -r                        remote server
  -l                        list sessions


"""
from docopt import docopt
import os
import sys
from os.path import expanduser, exists
from tmuxp import WorkspaceBuilder
from libtmux.server import Server
from libtmux import exc
import platform
import logging
import yaml

logging.basicConfig(level=logging.INFO)


formatted_hostname = platform.node().split('.')[0].lower()
default_inner_cmd = "tmuxpy inner {name} "
FROZEN = getattr(sys, 'frozen', False)


def get_env():
    env = dict(os.environ)  # make a copy of the environment
    lp_key = 'LD_LIBRARY_PATH'  # for Linux and *BSD.
    lp_orig = env.get(lp_key + '_ORIG')  # pyinstaller >= 20160820 has this
    if lp_orig is not None:
        env[lp_key] = lp_orig  # restore the original, unmodified value
    else:
        env.pop(lp_key, None)  # last resort: remove the env var
    return env



def window_config(name, window_config):
    return {
        'window_name': name,
        'panes': [
            {
                'shell_command': [
                    window_config.get(
                        'shell_command',
                        default_inner_cmd.format(
                            name=name
                        )
                    )
                ],
            },
        ],
    }


def session_config(name, config_map=None, windows=None):
    session_map = {
        'session_name': name,
        'start_directory': '~',
        'windows': windows or [],
        'options': {
            'base-index': 0
        },
    }
    if config_map is not None:
        config_map[name] = session_map
    return session_map


def get_status_line(host_config, remote):
    status_left = '#[fg={fg},bg={bg},bold] #S #[fg=colour238,bg=colour234,nobold]'
    status_right = "#[fg={fg},bg={bg},bold] #h "
    bg = host_config.get('bg', 'red') if remote else 'green'
    fg = host_config.get('fg', 'white') if remote else 'black'
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
        expanduser(args.get('--%s-config' % (conf_file.split('.')[0] or ''), '')),
        expanduser("~/.tmux/%s" % conf_file),
        expanduser("~/.tmuxpy/%s" % conf_file),
        expanduser("~/.local/etc/tmuxpy/%s" % conf_file),
        "/usr/local/etc/tmuxpy/%s" % conf_file,
        "/etc/tmuxpy/%s" % conf_file,
        ]
    for conf in config_locations:
        if exists(conf):
            return conf
    raise Exception(
        """No %s config found!!
Please set config in one of these locations:
%s""" % (conf_file, "\n".join(config_locations)))

if __name__ == "__main__":
    if FROZEN:
        os.environ['LD_LIBRARY_PATH'] = os.environ.get('LD_LIBRARY_PATH_ORIG', '')
    args = docopt(__doc__)
    print(args)
    server_name = args['<server>']
    session_name = args['<session>']
    remote = args['-r']  # or os.environ.get('SSH_TTY')
    kill = args['-k']
    os.environ['TERM'] = 'xterm-256color'
    os.chdir(expanduser("~"))

    host_config = {}
    for outer, inners in yaml.load(open(get_config(args['--windows-config'])))['windows'].items():
        session_config(
            outer,
            host_config,
            [
                window_config(name, config)
                for name, config in inners['windows'].items()
            ]
        )

    session_config = host_config.get(session_name, session_config(session_name))
    windows = session_config['windows']
    for i in range(10-len(windows)):
        session_config['windows'].append({
            'window_name': session_name,
            'panes': [
                {'shell_command': []}
            ]
        })

    server = Server(
        socket_path=expanduser("/tmp/tmux_%s_socket" % server_name),
        #socket_name="tmux_%s_new" % server_name,
        config_file=get_config("%s.conf" % server_name),
    )
    builder = WorkspaceBuilder(sconf=session_config, server=server)
    session = None
    if args.get('-k'):
        try:
            session = server.findWhere(
                {'session_name': session_name})
            session.kill_session()
        except Exception as e:
            logging.exception("Error killing session")
            pass
        exit(0)
    if args.get('-l'):
        print(server.list_sessions())
        exit(0)
    try:
        session = server.new_session(
            session_name=session_name)
    except exc.TmuxSessionExists:
        logging.debug("Session exists")
        pass
    try:
        builder.build(session)
    except exc.TmuxSessionExists:
        logging.debug("builder session exists")
        session = session or builder.session or server.findWhere(
            {'session_name': session_name})

    builder = WorkspaceBuilder(sconf=session_config, server=server)
    session = None
    sessions = None
    try:
        sessions = server.list_sessions()
        session = [s for s in sessions if s['session_name'] == session_name]
    except exc.TmuxpException:
        pass
    if not session:
        session = server.new_session(
            session_name=session_name, kill_session=True)
        builder.build(session)
    else:
        session = session.pop()

    if server_name == "outer":
        session.set_option("status-position", "top")
    else:
        session.set_option("status-position", "bottom")

    if not args['-d']:
        server.cmd("detach-client", "-s", session_name)


    status_right, status_left = get_status_line(host_config, remote)
    for session in server.list_sessions():
        try:
            session.set_option("status-right", status_right)
            session.set_option("status-left", status_left)
            session.set_environment('SSH_AUTH_SOCK', os.environ.get('SSH_AUTH_SOCK'))
            session.set_environment('SSH_AGENT_PID', os.environ.get('SSH_AGENT_PID'))
            if not remote:
                session.cmd('set-environment', '-gu', 'SSH_HOST_STR')
                session.cmd('set-environment', '-gu', 'SSH_TTY_SET')
            session.cmd("set_option", '-g', 'allow-rename', 'on')
            session.cmd("set_option", '-g', 'automatic-rename', 'on')
        except Exception:
            logging.exception("error setting up session")

    if not args['-d']:
        if 'TMUX' in os.environ and server_name == 'outer':
            os.system('tmux rename-window %s' % session_name)
        server.attach_session(session_name)
