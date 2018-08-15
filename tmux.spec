# -*- mode: python -*-

block_cipher = None


a_tmux = Analysis(
    ['tmux.py'],
    pathex=['/usr/local/etc/tmux'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
a_autossh = Analysis(
    ['autossh.py'],
    pathex=['/usr/local/etc/tmux'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
MERGE(
    (a_tmux,'tmux', 'tmux'),
    (a_tmux, 'tmux', 'tmux'),
)
pyz_tmux = PYZ(
    a_tmux.pure,
    a_tmux.zipped_data,
    cipher=block_cipher,
)
exe_tmux = EXE(
    pyz_tmux,
    a_tmux.scripts,
    a_tmux.binaries,
    a_tmux.zipfiles,
    a_tmux.datas,
    name='tmuxpy',
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,
)

pyz_autossh = PYZ(
    a_autossh.pure,
    a_autossh.zipped_data,
    cipher=block_cipher,
)
exe_autossh = EXE(
    pyz_autossh,
    a_autossh.scripts,
    a_autossh.binaries,
    a_autossh.zipfiles,
    a_autossh.datas,
    name='autosshpy',
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,
)
