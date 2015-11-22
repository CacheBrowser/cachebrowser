from setuptools import setup
from setuptools.command.install import install

setup(
    name='cachebrowser',
    version='0.1.0',
    packages=['cachebrowser'],
    license='',
    long_description=open('README.md').read(),
    package_data={'': ['*.json']},
    scripts=['scripts/cachebrowser'],
    install_requires=('gevent'),
)


