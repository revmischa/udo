#!/usr/bin/env python

from __future__ import print_function
from setuptools import setup, find_packages
import io
import codecs
import os
import sys

import udo

here = os.path.abspath(os.path.dirname(__file__))

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)

long_description = read('README.md')

setup(
    name='udo',
    version=udo.__version__,
    url='http://github.com/revmischa/udo',
    license='Anyone But RMS',
    author='Mischa Spiegemock',
    tests_require=['pytest'],
    install_requires=[
        'Boto>=2.36.0',
        'PyYAML',
        'parallel-ssh',
    ],
    author_email='revmischa@cpan.org',
    description='Automate AWS Deployments',
    long_description=long_description,
    packages=['udo'],
    include_package_data=True,
    platforms='any',
    test_suite='tests',
    entry_points={
        'console_scripts': [
            'udo = udo.main:invoke_console',
        ],
    },
    keywords='devops aws amazon autoscaling orchestration',
    classifiers=[
        'Programming Language :: Python',
        'Topic :: System :: Systems Administration'
    ]
)
