from setuptools import setup
import os

datafiles = [(root, [os.path.join(root, f) for f in files]) for root, dirs, files in os.walk('data')]

setup(
    name='CacheBrowser',
    version='0.1dev',
    author='Hadi Zolfaghari',
    author_email='hadi@cs.umass.edu',
    url='https://www.cachebrowser.net',
    license='MIT',
    packages=[
        'cachebrowser',
        'cachebrowser.api',
        'cachebrowser.settings'
    ],
    scripts=['bin/cachebrowser'],
    data_files=datafiles,
    install_requires=[
        'mitmproxy>=0.17',
        'peewee',
        'websocket-server',
        'appdirs',
        'colorama',
        'termcolor',
        'ipwhois',
    ],
)
