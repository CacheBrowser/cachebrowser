from setuptools import setup
from setuptools.command.install import install

setup(
    name='cachebrowser',
    version='0.1.0',
    url='https://cachebrowser.info',
    description='A proxy-less censorship resistance tool',
    long_description=open('README.md').read(),
    maintainer='Hadi Zolfaghari',
    maintainer_email='hadi@cs.umass.edu',
    license='',
    packages=['cachebrowser', 'cachebrowser/extensions'],
    package_data={'': ['*.json']},
    scripts=['scripts/cachebrowser'],
    install_requires=[
        'gevent>=1.0.2',
        'six>=1.10.0',
    ],
)


