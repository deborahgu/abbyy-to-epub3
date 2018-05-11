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

import execjs
import logging

from epubcheck import EpubCheck
from pprint import pformat


class EpubVerify(object):
    """
    Provides tools for verifying the quality of the EPUB,
    using common libraries such as EPUBcheck.
    Where sensible, provides tools for automatically parsing the output.
    """

    def __init__(self, debug=False):
        self.logger = logging.getLogger(__name__)
        self.debug = debug
        if self.debug:
            self.logger.addHandler(logging.StreamHandler())
            self.logger.setLevel(logging.DEBUG)

        self.results = {}

    def run_epubcheck(self, epub):
        """ Runs epubcheck and stores the output. """
        result = EpubCheck(epub)
        self.results['epubcheck'] = result

        if self.debug:
            if result.valid:
                self.logger.info("EpubCheck passed")
            else:
                self.logger.info("EpubCheck failed")
                print("EpubCheck result: {}\n{}".format(
                    result.valid,
                    pformat(result.messages),
                ))

        return result
