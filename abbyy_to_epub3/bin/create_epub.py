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

import argparse
import logging

from abbyy_to_epub3 import create_epub

logger = logging.getLogger(__name__)

usage = (
    "A directory containing all the necessary files.\n"
    "See the README at https://github.com/deborahgu/abbyy-to-epub3 for details."
)

parser = argparse.ArgumentParser(
    description='Process an ABBYY file into an EPUB'
)
parser.add_argument(
    '-d',
    '--debug',
    action='store_true',
    help='Show debugging information',
)
parser.add_argument('docname', help=usage)
parser.add_argument(
    '--epubcheck',
    default=False,
    action='store_true',
    help='Run EpubCheck on the newly created EPUB',
)
parser.add_argument(
    '--ace',
    default=False,
    action='store_true',
    help='Run DAISY Ace on the newly created EPUB',
)
args = parser.parse_args()

if args is not None:
    debug = args.debug
    if debug:
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)
    docname = args.docname
    book = create_epub.Ebook(
        docname,
        debug=debug,
        args=args,
    )
    book.craft_epub()
