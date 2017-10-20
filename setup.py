# Copyright 2017 Deborah Kaplan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup

setup(
    name="abbyy_to_epub3",
    version='1.0b1',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: Apache License",
        "Development Status :: 4 - Beta",
    ],
    keywords='epub abbyy accessibility epub3',
    python_requires='>=3',
    author='Deborah Kaplan',
    packages=['abbyy_to_epub3'],
    license='Apache',
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
