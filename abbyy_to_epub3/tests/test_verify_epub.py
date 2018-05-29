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

from abbyy_to_epub3.settings import TEST_DIR
from abbyy_to_epub3.verify_epub import EpubVerify

from tempfile import TemporaryDirectory

import pytest


class TestAbbyyParser(object):

    @pytest.fixture
    def ace_results(self):
        verifier = EpubVerify()
        with TemporaryDirectory() as d:
            verifier.run_ace(
                "{}/sample.epub".format(TEST_DIR), d
            )
        return verifier.results

    @pytest.fixture
    def epubcheck_results(self):
        verifier = EpubVerify()
        verifier.run_epubcheck(
            "{}/sample.epub".format(TEST_DIR)
        )
        return verifier.results

    def test_create_EpubVerify(self):
        """ Instantiate a verification object. """
        verifier = EpubVerify()
        assert verifier.results == {}

    def test_run_epubcheck(self, epubcheck_results):
        """ Running EPUBcheck on a good EPUB passes."""
        assert epubcheck_results['epubcheck'].valid

    def test_epubcheck_messages(self, epubcheck_results):
        """ Running EPUBcheck on a good EPUB stores the messages."""
        assert epubcheck_results['epubcheck'].messages[0][0] == 'PKG-012'

    def test_ace_messages(self, ace_results):
        """ Running Ace on an EPUB stores the messages."""
        expected = 4

        assert expected == len(ace_results['ace']['assertions'][0])

    def test_ace_test_subject(self, ace_results):
        """ Running Ace will report the file in which there are errors."""
        expected = u'xhtml/表紙.xhtml'

        assert expected == \
            ace_results['ace']['assertions'][1]['earl:testSubject']['url']

    def tesm_ace_impact(self, ace_results):
        """ Running Ace will report impact of any errors."""
        expected = 'minor'

        assert expected == \
            ace_results['ace']['assertions'][1]['assertions'][0]['earl:test']['earl:impact']
