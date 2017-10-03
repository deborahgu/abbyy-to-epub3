# -*- coding: utf-8 -*-

from ebooklib import epub
import pytest

from abbyy_to_epub3.parse_abbyy import AbbyyParser, sanitize_xml
from abbyy_to_epub3 import constants


class TestAbbyyParser(object):
    @pytest.fixture
    def finereader6(self):
        self.metadata = {}
        self.blocks = []
        self.paragraphs = {}

        parser = AbbyyParser(
            "abbyy_to_epub3/tests/finereader_6_sample.xml",
            "abbyy_to_epub3/tests/finereader_6_meta.xml",
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
            "abbyy_to_epub3/tests/finereader_10_sample.xml",
            "abbyy_to_epub3/tests/finereader_10_meta.xml",
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
