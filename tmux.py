#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tmux.py

Usage: tmux.py <server> <session> [options]

Options:
    --base-index=BASE_INDEX
    --window-name=WINDOW_NAME
    -c
    -d      Start detached
    -k      kill server
    -r      remote server
    -l      list sessions


"""
from docopt import docopt
import os
from os.path import expanduser
from tmuxp import Server, WorkspaceBuilder, exc
import platform


formatted_hostname = platform.node().split('.')[0].lower()
cmd = ("python %s inner {name} "
       "--base-index={base_index}") % __file__


def window_config(name, base_index=0):
    args = dict(name=name, base_index=base_index)
    return {
        'window_name': name,
        'panes': [
            {
                'shell_command': [
                    cmd.format(**args),
                ]
            },
        ],
    }


def session_config(name, config_map=None, windows=None, base_index=0):
    session_map = {
        'session_name': name,
        'start_directory': '~',
        'windows': windows or [],
        'options': {
            'base-index': base_index
        },
    }
    if config_map is not None:
        config_map[name] = session_map
    return session_map


wc = window_config
sc = session_config

series9 = {}
sc('left', series9, [wc('conf'), wc('dev')])
sc('right', series9, [wc('misc'), wc('devops')])
sc('xplan', series9)
sc('conf', series9)
sc('monitor', config_map=series9)
sc('media', config_map=series9)
sc('tleft', series9, [wc('txplan')])

acer = {}
sc('acer', acer)
webpi = {}
sc('webpi', webpi)

xbmc = {}
sc('raspbmc', config_map=xbmc)

iress = {
    'bg': 'red',
    'fg': 'white'
}

sc('left', config_map=iress, windows=[
    wc('xplan'),
    wc('manup'),
    wc('conf'),
], base_index=0)

sc('right', config_map=iress, windows=[
    wc('xplandev'),
    wc('manupdev'),
    wc('oscscope'),
    wc('misc'),
], base_index=0)

sc('comm', config_map=iress, windows=[
    wc('jabber'),
    wc('email'),
], base_index=0)

sc('tleft', config_map=iress, windows=[
    wc('txplan')], base_index=0)
sc('xplan', config_map=iress)
sc('manup', config_map=iress)
sc('xplandev', config_map=iress)
sc('manupdev', config_map=iress)
sc('conf', config_map=iress)
sc('jabber', config_map=iress)
sc('misc', config_map=iress)
sc('process', config_map=iress)

iress2 = dict(iress)
iress2['bg'] = 'blue'

config_map = {
    'steven-series9': series9,
    'acer': acer,
    'sydsjoseph-pc1': iress,
    'au02-sjosephpc2': iress2,
    'webpi': webpi,
    'xbmc': xbmc,
    'raspbmc': xbmc,
}


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


if __name__ == "__main__":
    args = docopt(__doc__)
    print(args)
    server_name = args['<server>']
    session_name = args['<session>']
    base_index = int(args['--base-index'] or 0)
    shell_command = args['-c'] or ''
    remote = args['-r']  # or os.environ.get('SSH_TTY')
    kill = args['-k']
    os.environ['TERM'] = 'xterm-256color'

    host_config = config_map.get(formatted_hostname, {})
    session_config = host_config.get(session_name, sc(session_name))
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
        config_file=expanduser("~/.tmux/%s.conf" % server_name))
    builder = WorkspaceBuilder(sconf=session_config, server=server)
    session = None
    if args.get('-k'):
        try:
            session = server.findWhere(
                {'session_name': session_name})
            session.kill_session()
        except Exception as e:
            print(e)
            pass
        exit(0)
    if args.get('-l'):
        print(server.list_sessions())
        exit(0)
    try:
        session = server.new_session(
            session_name=session_name)
    except exc.TmuxSessionExists:
        print("Session exists")
        pass
    try:
        builder.build(session)
    except exc.TmuxSessionExists:
        print("builder session exists")
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

    session.set_option('base-index', base_index)

    status_right, status_left = get_status_line(host_config, remote)
    print(status_right)
    print(status_left)
    for session in server.list_sessions():
        print(session.get('session_name'))
        session.set_option("status-right", status_right)
        session.set_option("status-left", status_left)
        session.set_environment('SSH_AUTH_SOCK', os.environ.get('SSH_AUTH_SOCK'))
        session.set_environment('SSH_AGENT_PID', os.environ.get('SSH_AGENT_PID'))
        if not remote:
            session.cmd('set-environment', '-gu', 'SSH_HOST_STR')
            session.cmd('set-environment', '-gu', 'SSH_TTY_SET')
        session.cmd("set_option", '-g', 'allow-rename', 'on')
        session.cmd("set_option", '-g', 'automatic-rename', 'on')

    if not args['-d']:
        if 'TMUX' in os.environ:
            os.system('tmux rename-window %s' % session_name)
        server.attach_session(session_name)
