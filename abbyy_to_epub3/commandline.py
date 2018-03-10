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

import argparse
import logging

from abbyy_to_epub3 import create_epub

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Process an ABBYY file into an EPUB.\n'
            "See README at https://github.com/deborahgu/abbyy-to-epub3 "
            "for details."
        )
    )
    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help='Show debugging information',
    )
    parser.add_argument(
        'item_dir', help="The file path where this item\'s files are kept.",
    )
    parser.add_argument(
        'item_identifier', help="The unique ID of this item.",
    )
    parser.add_argument(
        'item_bookpath', help=(
            "The prefix to a specific book within an item."
            "In a simple book, usually the same as the item_identifier."
        ),
    )
    parser.add_argument(
        '-o',
        '--out',
        default=None,
        help='Output path for epub',
    )
    parser.add_argument(
        '--tmpdir',
        default=None,
        help='Specify custom path for tmp abbyy and jp2 files'
    )
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
        book = create_epub.Ebook(
            args.item_dir,
            args.item_identifier,
            args.item_bookpath,
            tmpdir=args.tmpdir,
            debug=debug,
            args=args,
        )
        book.craft_epub(epub_outfile=args.out or 'out.epub')

if __name__ == "__main__":
    main()
