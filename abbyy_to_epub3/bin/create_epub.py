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

from abbyy_to_epub3 import create_epub
import sys

docname = sys.argv[1]
usage = (
    "Usage: python create_epub.py [docname], where [docname] is a directory "
    "containing all the necessary files.\n"
    "See the README at https://github.com/deborahgu/abbyy-to-epub3 for details."
        )

if docname:
    create_epub.craft_epub(docname)
else:
    print(usage)
