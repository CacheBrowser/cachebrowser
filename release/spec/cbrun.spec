# -*- mode: python -*-

block_cipher = None


a = Analysis(['cbrun.py'],
             pathex=['..', '.'],
             binaries=None,
             datas=[('../../data', 'data')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='cachebrowser',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='cachebrowser')
app = BUNDLE(coll,
             name='cachebrowser.app',
             icon=None,
             bundle_identifier=None)