# Copyright 2017 Deborah Kaplan
#
# This file is part of Abbyy-to-epub3.
# Source code is available at <https://github.com/deborahgu/abbyy-to-epub3>.
#
# Abbyy-to-epub3 is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from setuptools import setup

def requirements():
    """Returns requirements.txt as a list usable by setuptools"""
    here = os.path.abspath(os.path.dirname(__file__))
    reqtxt = os.path.join(here, u'requirements.txt')
    with open(reqtxt) as f:
        return f.read().split()

setup(
    name="abbyy_to_epub3",
    version='1.2',
    description='Converts abbyy files to epub3',
    url='https://github.com/internetarchive/abbyy-to-epub3',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Development Status :: 4 - Beta",
    ],
    keywords='epub abbyy accessibility epub3',
    author='Deborah Kaplan',
    author_email='deborah.kaplan@suberic.net',
    packages=['abbyy_to_epub3'],
    license='AGPLv3+',
    zip_safe=False,
    install_requires=requirements(),
    package_data={
        'abbyy_to_epub3': ['config.ini']
    },
    entry_points={
        'console_scripts': ['abbyy2epub=abbyy_to_epub3.commandline:main'],
    }
)
