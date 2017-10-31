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

from abbyy_to_epub3.verify_epub import EpubVerify


class TestAbbyyParser(object):

    def test_create_EpubVerify(self):
        """ Instantiate a verification object. """
        verifier = EpubVerify()
        assert verifier.results == {}

    def test_run_epubcheck(self):
        """ Running EPUBcheck on a good EPUB passes."""
        verifier = EpubVerify()
        verifier.run_epubcheck(
            "abbyy_to_epub3/tests/sample.epub"
        )

        assert verifier.results['epubcheck'].valid

    def test_epubcheck_messages(self):
        """ Running EPUBcheck on a good EPUB stores the messages."""
        verifier = EpubVerify()
        verifier.run_epubcheck(
            "abbyy_to_epub3/tests/sample.epub"
        )

        assert verifier.results['epubcheck'].messages[0][0] == 'PKG-012'

    def test_run_ace(self):
        """ Running EPUBcheck on a good EPUB currently does nothing."""
        verifier = EpubVerify()
        verifier.run_ace(
            "abbyy_to_epub3/tests/sample.epub"
        )

        assert 'ace' not in verifier.results
