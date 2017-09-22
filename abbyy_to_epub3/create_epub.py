# Copyright 2017 Deborah Kaplan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ebooklib import epub
from PIL import Image

import gzip
import logging
import os
import sys
import tempfile
from zipfile import ZipFile

from abbyy_to_epub3.parse_abbyy import AbbyyParser


logger = logging.getLogger(__name__)


class Ebook(object):
    """
    The Ebook object.

    Holds extracted information about a book & the Ebooklib EPUB object.
    """
    base = ''         # the book's identifier, used in many filename
    metadata = {}     # the book's metadata
    blocks = []       # each text or non-text block, with contents & attributes
    paragraphs = {}   # paragraph style info
    tmpdir = ''       # stores converted images and extracted zip files
    abbyy_file = ''   # the ABBYY XML file
    cover_img = ''    # the name of the cover image
    chapters = []     # holds each of the chapter (EpubHtml) objects
    progression = ''  # page direction
    pagelist = ''     # holds tthe page-list item

    book = epub.EpubBook()  # the book itself

    def __init__(self, base):
        self.base = base
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cover_img = '{}/cover.png'.format(self.tmpdir.name)
        self.abbyy_file = "{tmp}/{base}_abbyy".format(
            tmp=self.tmpdir.name, base=self.base
        )
        logger.debug("Temp: {}\n Base: {}".format(
            self.tmpdir.name, self.base))

    def extract_images(self):
        """
        Extracts all of the images for the text.

        For efficiency's sake, do these all at once. Memory and CPU will be at a
        higher premium than disk space, so unzip the entire scan file into a temp
        directory, instead of extracting only the needed images.
        """
        images_zipped = "{base}/{base}_jp2.zip".format(base=self.base)
        cover_file = "{tmp}/{base}_jp2/{base}_0001.jp2".format(
            tmp=self.tmpdir.name, base=self.base
        )
        with ZipFile(images_zipped) as f:
            f.extractall(self.tmpdir.name)

        # convert the JP2K file into a PNG for the cover
        f, e = os.path.splitext(os.path.basename(cover_file))
        try:
            Image.open(cover_file).save(self.cover_img)
        except IOError as e:
            logger.warning("Cannot create cover file: {}".format(e))

    def make_chapter(self, heading, chapter_no):
        """
        Create a chapter section in an ebooklib.epub.
        """
        if not heading:
            heading = "Chapter {}".format(chapter_no)

        chapter = epub.EpubHtml(
            title=heading,
            direction=self.progression,
            # pad out the filename to four digits
            file_name='chap_{:0>4}.xhtml'.format(chapter_no),
            lang='{}'.format(self.metadata['language'][0])
        )
        chapter.content = u''
        chapter.add_link(
            href='style/nav.css', rel='stylesheet', type='text/css'
        )
        self.chapters.append(chapter)
        self.book.add_item(chapter)

        return chapter

    def craft_html(self):
        """
        Assembles the XHTML content.

        Create some minimal navigation:
        * Break sections at text elements marked role: heading
        * Break files at any headings with roleLevel: 1
        This is imperfect, but better than having no navigation or monster files.

        Images will get the alternative text of "Picture #" followed by an index
        number for this image in the document. Barring real alternative text for
        true accessibility, this at least adds some identifying information.
        """

        # Default section to hold cover image & everything until the first heading
        heading = "Cover"
        chapter_no = 1
        picnum = 1
        pagelist_html = '<nav epub:type="page-list" hidden="">'
        pagelist_html += '<h1>List of Pages</h1>'
        pagelist_html += '<ol>'

        # Make the initial chapter stub
        chapter = self.make_chapter(heading, chapter_no)

        for block in self.blocks:
            if 'type' not in block:
                continue
            if block['type'] == 'Text':
                if 'heading' not in block:
                    # Regular text block. Add its heading to the chapter content.
                    chapter.content += u'<p>{}</p>'.format(block['text'])
                elif int(block['heading']) > 1:
                    # Heading >1. Format as heading but don't make new chapter.
                    chapter.content += u'<h{level}>{text}</h{level}>'.format(
                        level=block['heading'], text=block['text']
                    )
                else:
                    # Heading 1. Begin the new chapter
                    chapter_no += 1
                    chapter = self.make_chapter(heading, chapter_no)

                    heading = block['text']
                    chapter.content = u'<h{level}>{text}</h{level}>'.format(
                        level=block['heading'], text=heading
                    )
            elif block['type'] == 'Page':
                chapter.add_pageref(str(block['text']))
            elif block['type'] == 'Picture':
                # Image
                # pad out the filename to four digits
                origfile = '{dir}/{base}_jp2/{base}_{page:0>4}.jp2'.format(
                    dir=self.tmpdir.name,
                    base=self.base,
                    page=block['page_no']
                )
                basefile = 'img_{:0>4}.png'.format(picnum)
                pngfile = '{}/{}'.format(self.tmpdir.name, basefile)
                in_epub_imagefile = 'images/{}'.format(basefile)

                # get image dimensions from ABBYY block attributes
                left = int(block['style']['l'])
                top = int(block['style']['t'])
                right = int(block['style']['r'])
                bottom = int(block['style']['b'])
                box = (left, top, right, bottom)
                width = right - left
                height = bottom - top

                # make the image:
                try:
                    i = Image.open(origfile)
                except IOError as e:
                    logger.warning("Can't open image {}: {}".format(origfile, e))
                try:
                    i.crop(box).save(pngfile)
                except IOError as e:
                    logger.warning("Can't crop image {} and save to {}: {}".format(
                        origfile, pngfile, e
                    ))
                epubimage = epub.EpubImage()
                epubimage.file_name = in_epub_imagefile
                with open(pngfile, 'rb') as f:
                    epubimage.content = f.read()
                epubimage = self.book.add_item(epubimage)

                chapter.content += u'<img src="{src}" alt="Picture #{picnum}" width="{w}" height={h}>'.format(
                    src=in_epub_imagefile,
                    picnum=picnum,
                    w=width,
                    h=height,)

                # increment the image number
                picnum += 1
            elif block['type'] in ('Separator' or 'SeparatorsBox'):
                # Separator blocks seem to be fairly randomly applied and don't
                # correspond to anything useful in the original content
                pass
            else:
                logger.debug("Ignoring Block:\n Type: {}\n Attribs: {}".format(
                    block['type'], block['style']))

    def craft_epub(self):
        """ Assemble the extracted metadata & text into an EPUB  """

        # document files and directories
        abbyy_file_zipped = "{base}/{base}_abbyy.gz".format(base=self.base)
        metadata_file = "{base}/{base}_meta.xml".format(base=self.base)

        # Unzip the ABBYY file to disk. (Might be too huge to hold in memory.)
        with gzip.open(abbyy_file_zipped, 'rb') as infile:
            with open(self.abbyy_file, 'wb') as outfile:
                for line in infile:
                    outfile.write(line)

        # Extract the page images and create the cover file
        self.extract_images()

        # parse the ABBYY
        parser = AbbyyParser(
            self.abbyy_file,
            metadata_file,
            self.metadata,
            self.paragraphs,
            self.blocks
        )
        parser.parse_abbyy()

        # Text direction: convert IA abbreviation to ebooklib abbreviation
        direction = {
            'lr': 'ltr',
            'rl': 'rtl',
        }
        if 'page-progression' in self.metadata:
            self.progression = direction[self.metadata['page-progression'][0]]
        else:
            self.progression = 'default'
        self.book.set_direction(self.progression)

        # make the HTML chapters
        self.craft_html()

        # Set the book's metadata and cover
        self.book.set_cover('images/cover.png', open(self.cover_img, 'rb').read())
        for identifier in self.metadata['identifier']:
            self.book.set_identifier(identifier)
        for language in self.metadata['language']:
            self.book.set_language(language)
        for title in self.metadata['title']:
            self.book.set_title(title)
        if 'creator' in self.metadata:
            for creator in self.metadata['creator']:
                self.book.add_author(creator)
        if 'description' in self.metadata:
            for description in self.metadata['description']:
                self.book.add_metadata('DC', 'description', description)
        if 'publisher' in self.metadata:
            for publisher in self.metadata['publisher']:
                self.book.add_metadata('DC', 'publisher', publisher)

        # Navigation for EPUB 3 & EPUB 2 fallback
        self.book.toc = self.chapters
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        self.book.spine = ['nav'] + self.chapters

        # define CSS style
        style = '.center {text-align: center}'
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        self.book.add_item(nav_css)

        epub.write_epub('{base}/{base}.epub'.format(base=self.base), self.book, {})

        # clean up
        # ebooklib doesn't clean up cleanly without reset, causing problems on
        # consecutive runs
        self.tmpdir.cleanup()
        self.book.reset()
