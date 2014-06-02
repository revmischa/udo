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
    url='http://github.com/doctorbase/udo/',
    license='Anyone But RMS',
    author='Mischa Spiegemock',
    tests_require=['pytest'],
    install_requires=[
        'Boto>=2.0.0',
        'PyYAML',
    ],
    author_email='mischa@doctorbase.com',
    description='Automate AWS deployments',
    long_description=long_description,
    packages=['udo'],
    include_package_data=True,
    platforms='any',
    test_suite='tests',
    scripts=['udo'],
    classifiers=[
        'Programming Language :: Python',
        # ....
    ]
)
