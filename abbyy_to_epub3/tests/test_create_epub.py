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

from collections import OrderedDict
from ebooklib import epub
import json
import pytest

from abbyy_to_epub3.create_epub import Ebook
from abbyy_to_epub3.settings import TEST_DIR


class TestAbbyyParser(object):

    @pytest.fixture
    def metadata(self):
        with open("{}/parsed_metadata.json".format(TEST_DIR)) as f:
            md = json.load(f)
        return md

    @pytest.fixture
    def blocks(self):
        with open("{}/parsed_blocks.json".format(TEST_DIR)) as f:
            b = json.load(f)
        return b

    @pytest.fixture
    def paragraphs(self):
        with open("{}/parsed_paragraphs.json".format(TEST_DIR)) as f:
            p = json.load(f)
        return p

    @pytest.fixture
    def book(self):
        book = Ebook(base='testing')
        return book

    def test_create_Ebook(self, book):
        """ Instantiate an Ebook object. """
        assert book.base == 'testing'

    def test_create_accessibility_metadata(self, book):
        """ Set the accessibility metadata of a default book. """
        book.create_accessibility_metadata()

        accessibility_metadata = book.book.metadata[None]['meta']

        assert 'The publication was generated' in accessibility_metadata[0][0]
        assert accessibility_metadata[0][1] == OrderedDict(
            [('property', 'schema:accessibilitySummary')])

    def test_set_metadata(self, metadata, book, monkeypatch):
        """ Verifies metadata from the dict parsed from the metadata file """
        monkeypatch.setattr(Ebook, 'metadata', metadata)
        book.set_metadata()

        assert book.book.title == 'Fire'
        assert book.book.language == 'eng'
        assert book.book.get_metadata(
            'http://purl.org/dc/elements/1.1/', 'creator'
        )[0][0] == 'Cashore, Kristin'

    def test_craft_html_chapters(self, blocks, metadata, book, monkeypatch):
        """ tests chapters created from the parsed blocks """
        monkeypatch.setattr(Ebook, 'metadata', metadata)
        monkeypatch.setattr(Ebook, 'blocks', blocks)
        monkeypatch.setattr(Ebook, 'make_image', lambda Ebook, str: '<img />')
        book.craft_html()

        assert len(book.chapters) == 2
        assert len(book.book.items) == 2
        assert book.chapters[1].title == "FIRE"
        assert '<p class="" style="font-size: 6pt">An imprint' in book.chapters[1].content
        assert book.chapters[1].file_name == 'chap_0002.xhtml'

    def test_make_chapter(self, metadata, book, monkeypatch):
        """
        create a chapter. By default the book has an opening section.
        """
        monkeypatch.setattr(Ebook, 'metadata', metadata)
        book.make_chapter("Chapter name", 3)

        assert len(book.chapters) == 3
        assert len(book.book.items) == 3
        assert book.chapters[2].title == "Chapter name"
        assert book.chapters[2].content == u''
        assert book.chapters[2].file_name == 'chap_0003.xhtml'
