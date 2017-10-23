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

from setuptools import setup

setup(
    name="abbyy_to_epub3",
    version='1.0b1',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Development Status :: 4 - Beta",
    ],
    keywords='epub abbyy accessibility epub3',
    python_requires='>=3',
    author='Deborah Kaplan',
    packages=['abbyy_to_epub3'],
    license='AGPLv3+',
    zip_safe=False,

    install_requires=[
        'ebooklib',
        'epubcheck',
        'fuzzywuzzy',
        'lxml',
        'Pillow',
        'PyExecJs',
        'pytest',
        'numeral',
        'sphinx',
        'sphinx-autobuild',
    ],

    entry_points={
        'console_scripts': ['abbyy_to_epub3/bin/create_epub.py'],
    }
)
