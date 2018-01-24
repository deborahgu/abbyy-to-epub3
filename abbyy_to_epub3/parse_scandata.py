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

from lxml import etree

import logging


class ScandataParser(object):
    """
    The scandata parser object.
    Reads the page-by-page scanner information from a scandata.xml file.

    """

    def __init__(self, scandata, pages, debug=False):
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.addHandler(logging.StreamHandler())
            self.logger.setLevel(logging.DEBUG)

        self.pages = pages
        self.document = scandata

    def parse_scandata(self):
        """ read the scandata file into an lxml etree """
        self.tree = etree.parse(self.document)

        pagelist = self.tree.findall("./pageData/page")
        for page in pagelist:
            num = page.get('leafNum')
            pagetype = page.find('pageType').text
            self.pages[int(num)] = pagetype
