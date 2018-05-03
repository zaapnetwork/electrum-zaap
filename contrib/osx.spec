# -*- mode: python -*-
import sys


for i, x in enumerate(sys.argv):
    if x == '--name':
        cmdline_name = sys.argv[i+1]
        break
else:
    raise BaseException('no name')

hiddenimports = [
    'lib',
    'lib.base_wizard',
    'lib.plot',
    'lib.qrscanner',
    'lib.websockets',
    'gui.qt',

    'memonic',  # required by python-trezor

    'plugins',

    'plugins.hw_wallet.qt',

    'plugins.audio_modem.qt',
    'plugins.cosigner_pool.qt',
    'plugins.digitalbitbox.qt',
    'plugins.email_requests.qt',
    'plugins.keepkey.qt',
    'plugins.labels.qt',
    'plugins.trezor.qt',
    'plugins.ledger.qt',
    'plugins.virtualkeyboard.qt',
]

datas = [
    ('packages/requests/cacert.pem', 'packages/requests'),
    ('lib/currencies.json', 'electrum_zaap'),
    ('lib/wordlist', 'electrum_zaap/wordlist'),
]

# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
sys.modules['FixTk'] = None
excludes = ['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter']

a = Analysis(['electrum-zaap'],
             pathex=['plugins'],
             hiddenimports=hiddenimports,
             datas=datas,
             excludes=excludes,
             runtime_hooks=['pyi_runtimehook.py'])

# http://stackoverflow.com/questions/19055089/
for d in a.datas:
    if 'pyconfig' in d[0]:
        a.datas.remove(d)
        break

# Add TOC to electrum_zaap, electrum_zaap_gui, electrum_zaap_plugins
for p in sorted(a.pure):
    if p[0].startswith('lib') and p[2] == 'PYMODULE':
        a.pure += [('electrum_zaap%s' % p[0][3:] , p[1], p[2])]
    if p[0].startswith('gui') and p[2] == 'PYMODULE':
        a.pure += [('electrum_zaap_gui%s' % p[0][3:] , p[1], p[2])]
    if p[0].startswith('plugins') and p[2] == 'PYMODULE':
        a.pure += [('electrum_zaap_plugins%s' % p[0][7:] , p[1], p[2])]

pyz = PYZ(a.pure)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          debug=False,
          strip=False,
          upx=False,
          console=False,
          icon='icons/electrum-zaap.ico',
          name=os.path.join('build/electrum-zaap/electrum-zaap', cmdline_name))

# trezorctl separate bin
tctl_a = Analysis(['/usr/local/bin/trezorctl'],
                  hiddenimports=['pkgutil'],
                  excludes=excludes,
                  runtime_hooks=['pyi_tctl_runtimehook.py'])

tctl_pyz = PYZ(tctl_a.pure)

tctl_exe = EXE(tctl_pyz,
           tctl_a.scripts,
           exclude_binaries=True,
           debug=False,
           strip=False,
           upx=False,
           console=True,
           name=os.path.join('build/electrum-zaap/electrum-zaap', 'trezorctl.bin'))

coll = COLLECT(exe, tctl_exe,
               a.binaries,
               a.datas,
               strip=False,
               upx=False,
               name=os.path.join('dist', 'electrum-zaap'))

app = BUNDLE(coll,
             name=os.path.join('dist', 'Electrum-zaap.app'),
             appname="Electrum-zaap",
	         icon='electrum-zaap.icns',
             version = 'ELECTRUM_VERSION')
