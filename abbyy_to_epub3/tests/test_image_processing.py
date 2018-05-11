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

from PIL import Image

import mock
import subprocess

from abbyy_to_epub3.image_processing import factory as ImageFactory


class TestImageFactory(object):

    #
    # Image instantiation tests
    #
    def test_create_kakadu_image(self):
        """ Create an ImageProcessor object with type kakadu """
        # Because the image library factories are defined as local subclasses
        # of the factory function, "isinstance()" can't verify them. Check the
        # type with this hack instead.
        typestring = "KakaduProcessor"

        test_image = ImageFactory("kakadu")

        assert typestring in str(type(test_image))

    def test_create_pillow_image(self):
        """ Create an ImageProcessor object with type pillow """
        # Because the image library factories are defined as local subclasses
        # of the factory function, "isinstance()" can't verify them. Check the
        # type with this hack instead.
        typestring = "PillowProcessor"

        test_image = ImageFactory("pillow")

        assert typestring in str(type(test_image))

    #
    # Kakadu tests
    #
    @mock.patch("subprocess.run")
    def test_kakadu_uncropped_subprocess(self, mock_subprocess):
        """
        When working with Kakadu, a call to crop_image with no dimensions
        makes the subprocess call without a region string.
        """
        test_image = ImageFactory("kakadu")
        infile = 'input_filename'
        outfile = 'output_filename'
        expected = [
            'kdu_expand',
            '-reduce', '2',
            '-no_seek',
            '-i', 'input_filename',
            '-o', 'output_filename'
        ]

        test_image.crop_image(infile, outfile)
        mock_subprocess.assert_called_with(
            (expected), stdout=subprocess.DEVNULL, check=True
        )

    @mock.patch("subprocess.run")
    def test_kakadu_cropped_subprocess(self, mock_subprocess):
        """
        When working with Kakadu, a call to crop_image with provided
        dimensions makes the subprocess call with a region string.
        """
        test_image = ImageFactory("kakadu")
        infile = 'input_filename'
        outfile = 'output_filename'
        dim = [1, 2, 3, 4]
        pagedim = (1.0, 2.0)

        expected = [
            'kdu_expand',
            '-region', '{1.0,1.0},{1.0,2.0}',
            '-reduce', '2',
            '-no_seek',
            '-i', 'input_filename',
            '-o', 'output_filename',
        ]

        test_image.crop_image(infile, outfile, dim=dim, pagedim=pagedim)
        mock_subprocess.assert_called_with(
            (expected), stdout=subprocess.DEVNULL, check=True
        )

    #
    # Pillow tests
    #
    def test_pillow_uncropped(self):
        """
        When working with Pillow, a call to crop_image with no dimensions
        makes the call to save.
        """
        with mock.patch.object(Image, "open") as MockImage:
            test_image = ImageFactory("pillow")
            infile = 'input_filename'
            outfile = 'output_filename'
            expected = MockImage.save(outfile)

            test_image.crop_image(infile, outfile)

            # Did we open the file?
            MockImage.assert_called_with(infile)
            # Did we save the file?
            MockImage.assert_has_calls(expected)

    def test_pillow_cropped(self):
        """
        When working with Pillow, a call to crop_image with provided
        dimensions makes the call to crop.
        """
        with mock.patch.object(Image, "open") as MockImage:
            test_image = ImageFactory("pillow")
            infile = 'input_filename'
            outfile = 'output_filename'
            dim = [1, 2, 3, 4]
            pagedim = (1.0, 2.0)

            expected = MockImage.crop(infile, dim)

            test_image.crop_image(infile, outfile, dim=dim, pagedim=pagedim)

            # Did we open the file?
            MockImage.assert_called_with(infile)
            # Did we save the file?
            MockImage.assert_has_calls(expected)
