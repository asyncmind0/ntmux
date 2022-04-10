NTmux - Nested Tmux Config

![Nested Tmux](ntmux.png)

Setup

    git clone git@github.com:jagguli/ntmux.git ~/.tmux/
    cd .tmux/
    sh -x setup.sh

Initialize outer tmux ...

    tmuxpy outer term1
    
    
Initialize inner tmux ...

    tmuxpy inner work
    
Configure nesting in  `configs/default.yaml`
