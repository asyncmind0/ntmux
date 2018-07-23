#!/bin/sh -x
BASE_DIR=/usr/local/etc/zsh
if [ ! -d $BASE_DIR ]; then
    BASE_DIR=$HOME/.zsh
fi
if [ -z "$NO_PIP_INSTALL" ]; then
pip install -U --user -r $BASE_DIR/requirements.txt
fi
mkdir -p $HOME/.local/bin/
ln -sf $HOME/.tmux/autossh.py $HOME/.local/bin/
ln -sf $HOME/.tmux/tmux.py $HOME/.local/bin/
ln -sf $HOME/.tmux/inner.conf $HOME/.tmux.conf
