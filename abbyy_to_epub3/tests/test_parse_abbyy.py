# -*- coding: utf-8 -*-
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

from ebooklib import epub
import pytest

from abbyy_to_epub3.parse_abbyy import AbbyyParser, sanitize_xml
from abbyy_to_epub3.settings import TEST_DIR
from abbyy_to_epub3 import constants


class TestAbbyyParser(object):
    @pytest.fixture
    def finereader6(self):
        self.metadata = {}
        self.blocks = []
        self.paragraphs = {}

        parser = AbbyyParser(
            "{}/finereader_6_sample.xml".format(TEST_DIR),
            "{}/finereader_6_meta.xml".format(TEST_DIR),
            self.metadata,
            self.paragraphs,
            self.blocks,
        )

        return parser

    @pytest.fixture
    def finereader10(self):
        self.metadata = {}
        self.blocks = []
        self.paragraphs = {}

        parser = AbbyyParser(
            "{}/finereader_10_sample.xml".format(TEST_DIR),
            "{}/finereader_10_meta.xml".format(TEST_DIR),
            self.metadata,
            self.paragraphs,
            self.blocks,
        )

        return parser

    def test_parse_fr10_metadata(self, finereader10):
        """ Builds a dictionary from a FR10 _meta.xml file. """
        parser = finereader10
        parser.parse_metadata()

        assert 'Greek poetry' in self.metadata['subject']

    def test_parse_fr6_metadata(self, finereader6):
        """ Builds a dictionary from a FR6 _meta.xml file. """
        parser = finereader6
        parser.parse_metadata()

        assert '6428718' in self.metadata['local_id']

    def test_unicode(self, finereader6):
        """ Parse unicode characters correctly. """
        title = 'מנוח המלמד : או, גבר אשר דרכו נסתרה : ספור'
        parser = finereader6
        parser.parse_metadata()

        assert title in self.metadata['title-alt-script']

    def test_sanitize(self):
        """ Clean illegal characters out of XML text entities. """
        text = 'http://haxxor/evil.html?u=<img%20src="aaa"%20onerror=alert(1)>'
        good = 'http://haxxor/evil.html?u=&lt;img%20src=&quot;aaa&quot;%20onerror=alert(1)&gt;'

        result = sanitize_xml(text)

        assert result == good
