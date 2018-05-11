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

import logging
import subprocess


class ImageProcessor(object):
    """
    The image object.

    Can use various image processing libraries via factories.
    """
    def __init__(self, debug=False):
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.addHandler(logging.StreamHandler())
            self.logger.setLevel(logging.DEBUG)

    def convert2png(self, original, png, resize):
        im = Image.open(original)
        if resize:
            im = im.resize(resize)
        im.save(png, 'png')

def factory(type):

    class KakaduProcessor(ImageProcessor):
        def crop_image(self, origfile, outfile, discard_level=2, dim=False, pagedim=False):
            """
            Given an image object, save a crop of the entire image.
            Convert (left, top, right, bottom) in pixels to the format
            wanted by kakadu: "{<top>,<left>},{<height>,<width>}"
            as percentages between 0.0 and 1.0.
            Pagedim is passed as (width, height)
            """

            if dim and pagedim:
                # if dimensions are passed, save a crop of the image
                (left, top, right, bottom) = dim
                (pagewidth, pageheight) = pagedim
                region_string = "{%s,%s},{%s,%s}" % (
                    top / pageheight,
                    left / pagewidth,
                    (bottom - top) / pageheight,
                    (right - left) / pagewidth
                )
            else:
                region_string = "{0.0,0.0},{1.0,1.0}"

            # kdu_expand has to be run as a subprocess call
            cmd_bmp = [
                'kdu_expand',
                '-region', region_string,
                '-reduce', str(discard_level),
                '-no_seek',
                '-i', origfile,
                '-o', outfile + '.bmp'
            ]
            cmd_pnm = [
                'bmptopnm', outfile + '.bmp'
            ]
            cmd_png = 'pnmtopng'
            try:
                subprocess.run(
                    cmd_bmp, stdout=subprocess.DEVNULL, check=True
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    "Can't save cropped image as BMP: {}".format(e)
                )
            # We don't always control the filenames of the JP2, so use
            # subprocess.PIPE, not shell=True, to prevent injection
            try:
                p_pnm = subprocess.Popen(
                    cmd_pnm,
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    "Can't generate PNM: {}".format(e)
                )
            try:
                p_png = subprocess.Popen(
                    cmd_png,
                    stderr=subprocess.DEVNULL,
                    stdin=p_pnm.stdout,
                    stdout=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    "Can't generate PNG: {}".format(e)
                )

            # Write the PNG from the pipeline into a file
            # `pnmtopng` only writes to stdout
            pngout, pngerr = p_png.communicate()
            with open(outfile, 'wb') as fh:
                fh.write(pngout)


    class PillowProcessor(ImageProcessor):

        def crop_image(self, origfile, outfile, dim=False, pagedim=False):
            """
            Given an image object, save a crop or the entire image.
            Pagedim isn't used for Pillow processing but it's passed anyway
            because the caller doesn't know which library we use.
            """

            if dim:
                # if dimensions are passed, save a crop of the image
                try:
                    i = Image.open(origfile)
                except IOError as e:
                    raise RuntimeError(
                        "Can't open image {}: {}".format(origfile, e))
                try:
                    i.crop(dim).save(outfile)
                except IOError as e:
                    raise RuntimeError(
                        "Can't crop image {} & save to {}: {}".format(
                            origfile, outfile, e
                        )
                    )
            else:
                # save the entire image
                try:
                    Image.open(origfile).save(outfile)
                except IOError as e:
                    raise RuntimeError(
                        "Cannot create cover file: {}".format(e)
                    )

    if type == "kakadu":
        return KakaduProcessor()
    return PillowProcessor()
