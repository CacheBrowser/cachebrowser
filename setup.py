from distutils.command.install import install
from distutils.core import setup
import json
import os
import platform


CHROME_MANIFEST_FILE = 'com.spin.cachebrowser.json'


class CacheBrowserInstall(install):

    def run(self):
        install.run(self)

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

        if target_manif_dir is None:
            print("Unsupported platform %s" % plat)
            return

        try:
            os.makedirs(target_manif_dir)
        except os.error:
            pass

        os.chmod(chromeexec, 0755)

        target_manif_file = os.path.join(target_manif_dir, CHROME_MANIFEST_FILE)

        print("Generating Chrome manifest file in '%s'" % target_manif_file)

        with open(chromemanif, 'r') as base_manifest:
            manifest = json.loads(base_manifest.read())

        manifest['path'] = chromeexec

        with open(target_manif_file, 'w') as target_manifest:
            target_manifest.write(json.dumps(manifest, indent=4))


setup(
    name='CacheBrowser',
    version='0.1.0',
    packages=['cachebrowser', 'cachebrowser/chrome'],
    license='',
    long_description=open('README.md').read(),
    package_data={'': ['*.json']},
    scripts=['scripts/cachebrowser'],
    cmdclass={'install': CacheBrowserInstall}
)


