#!/bin/sh -x
BASE_DIR=/usr/local/etc/tmux
if [ ! -d $BASE_DIR ]; then
    BASE_DIR=$HOME/.tmux/
fi
if [ -z "$NO_PIP_INSTALL" ]; then
    pip install -U --user -r $BASE_DIR/requirements.txt
fi
mkdir -p $HOME/.local/bin/
wget -o tmuxpy.zip "https://gitlab.com/api/v4/projects/7957517/jobs/artifacts/master/download?job=docker"
ln -sf $HOME/.tmux/autossh.py $HOME/.local/bin/
ln -sf $HOME/.tmux/tmux.py $HOME/.local/bin/
ln -sf $HOME/.tmux/tmuxpy $HOME/.local/bin/
ln -sf $HOME/.tmux/inner.conf $HOME/.tmux.conf
