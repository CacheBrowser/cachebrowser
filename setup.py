# from distutils.core import setup
# from distutils.command.install import install
import json
import os
import platform
from setuptools import setup
from setuptools.command.install import install

COMP_NAME = 'com.spin.cachebrowser'
CHROME_MANIFEST_FILE = COMP_NAME + '.json'


class CacheBrowserInstall(install):

    def run(self):
        # For some reason this won't allow dependencies to be installed
        # install.run(self)
        # Using this instead
        install.do_egg_install(self)

        self.install_chrome_native_host()

    def install_chrome_native_host(self):
        lib_dir = self.install_lib
        proj_dir = os.path.join(lib_dir, 'cachebrowser')
        chrome_dir = os.path.join(proj_dir, 'chrome')
        chromeexec = os.path.join(chrome_dir, 'chromehost.py')
        chromemanif = os.path.join(chrome_dir, CHROME_MANIFEST_FILE)

        # For OSX/Linux only
        home_dir = os.path.expanduser("~")
        plat = platform.system()

        if plat == 'Windows':
            import _winreg

            target_manif_dir = os.path.join(os.environ['ALLUSERSPROFILE'], 'CacheBrowser')
            target_manif_file = os.path.join(target_manif_dir, CHROME_MANIFEST_FILE)

            def set_reg(name, value):
                REG_PATH = r'Software\Google\Chrome\NativeMessagingHosts'
                try:
                    _winreg.CreateKey(_winreg.HKEY_CURRENT_USER, REG_PATH)
                    registry_key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                                                   _winreg.KEY_WRITE)
                    _winreg.SetValueEx(registry_key, name, 0, _winreg.REG_SZ, value)
                    _winreg.CloseKey(registry_key)
                    return True
                except Exception as e:
                    print("Error: %s" % e.message)
                    return

            set_reg(COMP_NAME, target_manif_file)
        else:
            is_root = os.geteuid() == 0
            target_manif_dir = {
                'Darwin': {
                    True: "/Library/Google/Chrome/NativeMessagingHosts",
                    False: os.path.join(home_dir, "Library/Application Support/Google/Chrome/NativeMessagingHosts")
                },
                'Linux': {
                    True: "/etc/opt/chrome/native-messaging-hosts",
                    False: os.path.join(home_dir, ".config/google-chrome/NativeMessagingHosts")
                }
            }.get(plat, {}).get(is_root, None)
            target_manif_file = os.path.join(target_manif_dir, CHROME_MANIFEST_FILE)

            if target_manif_dir is None:
                print("Unsupported platform %s" % plat)
                return

            os.chmod(chromeexec, 0755)

        try:
            os.makedirs(target_manif_dir)
        except os.error:
            pass


        print("Generating Chrome manifest file in '%s'" % target_manif_file)

        with open(chromemanif, 'r') as base_manifest:
            manifest = json.loads(base_manifest.read())

        manifest['path'] = chromeexec

        with open(target_manif_file, 'w') as target_manifest:
            target_manifest.write(json.dumps(manifest, indent=4))


setup(
    name='cachebrowser',
    version='0.1.0',
    packages=['cachebrowser', 'cachebrowser/chrome'],
    license='',
    long_description=open('README.md').read(),
    package_data={'': ['*.json']},
    scripts=['scripts/cachebrowser'],
    install_requires=('gevent'),
    cmdclass={'install': CacheBrowserInstall}
)


