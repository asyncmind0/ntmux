pip install --user --upgrade -r requirements.txt
mkdir ~/.local/bin
mkdir -p ~/.local/bin
ln -sf ~/.tmux/autossh.py ~/.local/bin/
ln -sf ~/.tmux/tmux.py ~/.local/bin/
ln -sf ~/.tmux/inner.conf ~/.tmux.conf
