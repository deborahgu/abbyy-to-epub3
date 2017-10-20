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

from collections import OrderedDict
from ebooklib import epub
from fuzzywuzzy import fuzz
from numeral import roman2int
from PIL import Image
from pkg_resources import Requirement, resource_filename

from zipfile import ZipFile

import configparser
import gzip
import logging
import os
import re
import sys
import tempfile

from abbyy_to_epub3.parse_abbyy import AbbyyParser
from abbyy_to_epub3.utils import dirtify_xml, is_increasing
from abbyy_to_epub3.verify_epub import EpubVerify


# Set up configuration
config = configparser.ConfigParser()
configfile = resource_filename(Requirement.parse("abbyy_to_epub3"), "config.ini")
config.read(configfile)


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
    #pagelist = ''     # holds the page-list item
    firsts = {}       # all first lines per-page
    lasts = {}        # all last lines per-page
    # are there headers, footers, or page numbers?
    headers_present = False
    pagenums_found = False
    rpagenums_found = False
    table = False
    table_row = False
    table_cell = False

    book = epub.EpubBook()  # the book itself

    def __init__(self, base, debug=False, args=False):
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.addHandler(logging.StreamHandler())
            self.logger.setLevel(logging.DEBUG)

        self.debug = debug
        self.args = args
        self.base = base
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cover_img = '{}/cover.png'.format(self.tmpdir.name)
        self.abbyy_file = "{tmp}/{base}_abbyy".format(
            tmp=self.tmpdir.name, base=self.base
        )
        self.logger.debug("Temp directory: {}\nidentifier: {}".format(
            self.tmpdir.name, self.base))

    def create_accessibility_metadata(self):
        """ Set up accessibility metadata """
        ALT_TEXT_PRESENT = config.getboolean('Main', 'ALT_TEXT_PRESENT')
        IMAGES_PRESENT = config.getboolean('Main', 'IMAGES_PRESENT')
        OCR_GENERATED = config.getboolean('Main', 'OCR_GENERATED')
        TEXT_PRESENT = config.getboolean('Main', 'TEXT_PRESENT')

        summary = ''
        modes = []
        modes_sufficient = []
        features = ['printPageNumbers', 'tableOfContents', ]

        if OCR_GENERATED:
            summary += (
                'The publication was generated using automated character recognition, '
                'therefore it may not be an accurate rendition of the original text, '
                'and it may not offer the correct reading sequence.'
            )
        if IMAGES_PRESENT:
            modes.append('visual')
            if ALT_TEXT_PRESENT:
                features.append('alternativeText')
            else:
                summary += (
                    'This publication is missing meaningful alternative text.'
                )
        if TEXT_PRESENT:
            modes.append('textual')
            if IMAGES_PRESENT:
                modes_sufficient.append('textual,visual')
                if ALT_TEXT_PRESENT:
                    modes_sufficient.append('textual')
            else:
                modes_sufficient.append('textual')
        elif IMAGES_PRESENT and ALT_TEXT_PRESENT:
            modes_sufficient.append('textual,visual')
            modes_sufficient.append('visual')
        elif IMAGES_PRESENT:
            modes_sufficient.append('visual')
        if OCR_GENERATED:
            # these states will be true for any static content,  which we know
            # is guaranteed for OCR generated texts.
            hazards = [
                'noFlashingHazard',
                'noMotionSimulationHazard',
                'noSoundHazard',
            ]
            controls = [
                'fullKeyboardControl',
                'fullMouseControl',
                'fullSwitchControl',
                'fullTouchControl',
                'fullVoiceControl',
            ]

        if summary:
            summary += 'The publication otherwise meets WCAG 2.0 Level A.'
        else:
            summary = 'The publication meets WCAG 2.0 Level A.'

        # Add the metadata to the publication
        self.book.add_metadata(
            None,
            'meta',
            summary,
            OrderedDict([('property', 'schema:accessibilitySummary')])
        )
        for feature in features:
            self.book.add_metadata(
                None,
                'meta',
                feature,
                OrderedDict([('property', 'schema:accessibilityFeature')])
            )
        for mode in modes:
            self.book.add_metadata(
                None,
                'meta',
                mode,
                OrderedDict([('property', 'schema:accessMode')])
            )
        for mode_sufficient in modes_sufficient:
            self.book.add_metadata(
                None,
                'meta',
                mode_sufficient,
                OrderedDict([('property', 'schema:accessModeSufficient')])
            )
        if hazards:
            for hazard in hazards:
                self.book.add_metadata(
                    None,
                    'meta',
                    hazard,
                    OrderedDict([('property', 'schema:accessibilityHazard')])
                )
        if controls:
            for control in controls:
                self.book.add_metadata(
                    None,
                    'meta',
                    control,
                    OrderedDict([('property', 'schema:accessibilityControl')])
                )

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
            self.logger.warning("Cannot create cover file: {}".format(e))

    def image_dim(self, block):
        """
        Given a dict object containing the block info for an image, generate
        a tuple of its dimensions:
        (left, top, right, bottom)
        """
        left = int(block['style']['l'])
        top = int(block['style']['t'])
        right = int(block['style']['r'])
        bottom = int(block['style']['b'])

        return (left, top, right, bottom)

    def make_image(self, block):
        """
        Given a dict object containing the block info for an image, generate
        the image HTML
        """
        page_no = block['page_no']
        if page_no == 1:
            # The first page's image is made into the cover automatically
            return

        # pad out the filename to four digits
        origfile = '{dir}/{base}_jp2/{base}_{page:0>4}.jp2'.format(
            dir=self.tmpdir.name,
            base=self.base,
            page=block['page_no']
        )
        basefile = 'img_{:0>4}.png'.format(self.picnum)
        pngfile = '{}/{}'.format(self.tmpdir.name, basefile)
        in_epub_imagefile = 'images/{}'.format(basefile)

        # get image dimensions from ABBYY block attributes
        # (left, top, right, bottom)
        box = self.image_dim(block)
        width = box[2] - box[0]
        height = box[3] - box[1]

        # ignore if this image is entirely encapsulated in another image
        for each_pic in self.metadata['pics_by_page']:
            # Ignore if this is just the block itself
            if each_pic == block:
                continue
            new_box = self.image_dim(each_pic)
            for (old, new) in zip(box, new_box):
                if old <= new:
                    return

        # make the image:
        try:
            i = Image.open(origfile)
        except IOError as e:
            self.logger.warning("Can't open image {}: {}".format(origfile, e))
        try:
            i.crop(box).save(pngfile)
        except IOError as e:
            self.logger.warning("Can't crop image {} and save to {}: {}".format(
                origfile, pngfile, e
            ))
        epubimage = epub.EpubImage()
        epubimage.file_name = in_epub_imagefile
        with open(pngfile, 'rb') as f:
            epubimage.content = f.read()
        epubimage = self.book.add_item(epubimage)

        container_w = width / int(block['style']['pagewidth']) * 100
        content = u'''
        <div style="width: {c_w}%;">
        <img src="{src}" alt="Picture #{picnum}">
        </div>
        '''.format(
            c_w=container_w,
            src=in_epub_imagefile,
            picnum=self.picnum,
            w=width,
            h=height,)

        # increment the image number
        self.picnum += 1

        return content

    def make_chapter(self, heading, chapter_no):
        """
        Create a chapter section in an ebooklib.epub.
        """
        if not heading:
            heading = "Chapter {}".format(chapter_no)

        # The Ebooklib library escapes the XML itself
        chapter = epub.EpubHtml(
            title=dirtify_xml(heading).replace("\n", " "),
            direction=self.progression,
            # pad out the filename to four digits
            file_name='chap_{:0>4}.xhtml'.format(chapter_no),
            lang='{}'.format(self.metadata['language'][0])
        )
        chapter.content = u''
        chapter.add_link(
            href='style/style.css', rel='stylesheet', type='text/css'
        )
        self.chapters.append(chapter)
        self.book.add_item(chapter)

        return chapter

    def identify_headers_footers_pagenos(self, placement):
        """
        Attempts to identify the presence of headers, footers, or page numbers

        1. Build a dict of first & last lines, indexed by page number.
        2. Try to identify headers and footers.

        Headers and footers can appear on every page, or on alternating pages
        (for example if one page has header of the title, the facing page
        might have the header of the chapter name).

        They may include a page number, or the page number might be a
        standalone header or footer.

        The presence of headers and footers in the document does not mean they
        appear on every page (for example, chapter openings or illustrated
        pages sometimes don't contain the header/footer, or contain a modified
        version, such as a standalone page number).

        Page numbers may be in Arabic or Roman numerals.

        This method does not attempt to look for all edge cases. For example,
        it will not find:
        - constantly varied headers, as in a dictionary
        - page numbers that don't steadily increase
        - page numbers that were misidentified in the OCR process, eg. IO2
        - page numbers that have characters around them, eg. '* 45 *'
        """

        # running this on first lines or last lines?
        if placement == 'first':
            mylines = self.firsts
        else:
            mylines = self.lasts
        self.logger.debug("Looking for headers/footers: {}".format(placement))

        # Look for standalone strings of digits
        digits = re.compile(r'^\d+$')
        romans = re.compile(r'^[xicmlvd]+$')
        candidate_digits = []
        candidate_romans = []
        for block in self.blocks:
            if placement in block:
                line = block['text']
                ourpageno = block['page_no']
                mylines[ourpageno] = {'text': block['text']}
                pageno = digits.search(line)
                rpageno = romans.search(line, re.IGNORECASE)
                if rpageno:
                    # Is this a roman numeral?
                    try:
                        # The numeral.roman2int method is very permissive
                        # for archaic numeral forms, which is good.
                        num = roman2int(line)
                    except ValueError:
                        # not a roman numeral
                        pass
                    mylines[ourpageno]['ocr_roman'] = placement
                    candidate_romans.append(num)
                elif pageno:
                    mylines[ourpageno]['ocr_digits'] = placement
                    candidate_digits.append(int(line))

        # The algorithms to find false positives in page number candidates
        # are resource intensive, so this excludes anything where the candidate
        # numbers aren't monotonically increasing.
        if candidate_digits and is_increasing(candidate_digits):
            self.pagenums_found = True
            self.logger.debug("Page #s found: {}".format(candidate_digits))
        if candidate_romans and is_increasing(candidate_romans):
            self.rpagenums_found = True
            self.logger.debug("Roman page #s found: {}".format(candidate_romans))

        # identify match ratio
        fuzz_consecutive = 0
        fuzz_alternating = 0
        for k, v in mylines.items():
            # Check to see if there's still one page forward
            if k + 1 in mylines:
                ratio_consecutive = fuzz.ratio(v['text'], mylines[k + 1]['text'])
                mylines[k]['ratio_consecutive'] = ratio_consecutive
                fuzz_consecutive += ratio_consecutive
            # Check to see if there's still two pages forward
            if k + 2 in mylines:
                ratio_alternating = fuzz.ratio(v['text'], mylines[k + 2]['text'])
                mylines[k]['ratio_alternating'] = ratio_alternating
                fuzz_alternating += ratio_alternating

        # occasional similar first/last lines might happen in all texts,
        # so only identify headers & footers if there are many of them
        HEADERS_PRESENT_THRESHOLD = int(
            config.get('Main', 'HEADERS_PRESENT_THRESHOLD')
        )
        if len(mylines) > 2:
            average_consecutive = fuzz_consecutive / (len(mylines) - 1)
            average_alternating = fuzz_alternating / (len(mylines) - 2)
            self.logger.debug("{}: consecutive fuzz avg.: {}".format(
                placement,
                average_consecutive
            ))
            self.logger.debug("{}: alternating fuzz avg.: {}".format(
                placement,
                average_alternating
            ))
            if average_consecutive > HEADERS_PRESENT_THRESHOLD:
                if placement == 'first':
                    self.headers_present = 'consecutive'
                else:
                    self.footers_present = 'consecutive'
                self.logger.debug("{} repeated, consecutive pages".format(placement))
            elif average_alternating > HEADERS_PRESENT_THRESHOLD:
                if placement == 'first':
                    self.headers_present = 'alternating'
                else:
                    self.footers_present = 'alternating'
                self.logger.debug("{} repeated, alternating pages".format(placement))

    def is_header_footer(self, block, placement):
        """
        Given a block and our identified text structure, return True if this
        block's text is a header, footer, or page number to be ignored, False
        otherwise.
        """
        THRESHOLD = int(
            config.get('Main', 'FUZZY_HEADER_THRESHOLD')
        )

        # running this on first lines or last lines?
        if placement == 'first':
            mylines = self.firsts
        else:
            mylines = self.lasts

        ourpageno = block['page_no']
        if ourpageno in mylines:
            if (
                self.rpagenums_found and
                'ocr_roman' in mylines[ourpageno] and
                mylines[ourpageno]['ocr_roman'] == placement
            ):
                # This is an identified roman numeral page number
                return True
            if (
                self.pagenums_found and
                'ocr_digits' in mylines[ourpageno] and
                mylines[ourpageno]['ocr_digits'] == placement
            ):
                # This is an identified page number
                self.logger.debug("identified page number: {}".format(block['text']))
                return True
            if (
                self.headers_present == 'consecutive' and
                'ratio_consecutive' in mylines[ourpageno] and
                mylines[ourpageno]['ratio_consecutive'] >= THRESHOLD
            ):
                return True
            if (
                self.headers_present == 'alternating' and
                'ratio_alternating' in mylines[ourpageno] and
                mylines[ourpageno]['ratio_alternating'] >= THRESHOLD
            ):
                return True
        return False

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
        heading = "Opening Section"
        chapter_no = 1
        self.picnum = 1
        pagelist_html = '<nav epub:type="page-list" hidden="">'
        pagelist_html += '<h1>List of Pages</h1>'
        pagelist_html += '<ol>'
        blocks_index = -1
        self.last_row = False

        # Look for headers and page numbers
        # FR10 has markup but isn't reliable so look there as well
        self.identify_headers_footers_pagenos('first')
        self.identify_headers_footers_pagenos('last')
        self.last_row = False
        self.last_cell = False

        # Make the initial chapter stub
        chapter = self.make_chapter(heading, chapter_no)

        for block in self.blocks:
            blocks_index += 1

            if 'type' not in block:
                continue
            if (
                'style' in block and
                'fontstyle' in block['style']
            ):
                fclass = ''
                fontstyle = block['style']['fontstyle']
                fsize = fontstyle['fs']
                if 'italic' in fontstyle:
                    fclass += 'italic '
                if 'bold' in fontstyle:
                    fclass += 'bold '
                if 'Serif' in fontstyle['ff'] or 'Times' in fontstyle['ff']:
                    fclass += 'serif '
                elif 'Sans' in fontstyle['ff']:
                    fclass += 'sans '

                fstyling = 'class="{fclass}" style="font-size: {fsize}pt"'.format(
                    fclass=fclass,
                    fsize=fsize,
                )
            else:
                fstyling = ''
            if block['type'] == 'Text':
                text = block['text']
                role = block['role']

                # This is the first text element on the page
                if 'first' in block:
                    # reset any footnote references
                    noteref = 1

                    # Look for headers and page numbers
                    if self.is_header_footer(block, 'first'):
                        self.logger.debug("Stripping header {}".format(text))
                        continue

                # Look for footers and page numbers
                if (
                    'last' in block and
                    self.is_header_footer(block, 'last')
                ):
                        self.logger.debug("Stripping footer {}".format(text))
                        continue
                if role == 'footnote':
                    # footnote. Our ABBYY markup doesn't indicate references,
                    # so fake them, right above the footnote content so they'll
                    # be reachable by all adaptive tech and user agents.
                    chapter.content += u'<p><a epub:type="noteref" href="#n{page}_{ref}">{ref}</a></p>'.format(
                        page=block['page_no'],
                        ref=noteref,
                    )
                    chapter.content += u'<aside epub:type="footnote" id="n{page}_{ref}">{text}</aside>'.format(
                        page=block['page_no'],
                        ref=noteref,
                        text=text,
                    )
                    noteref += 1
                elif role == 'tableCaption':
                    # It would be ideal to mark up table captions as <caption>
                    # within the associated table.  However, the ABBYY markup
                    # doesn't have a way to associate the caption with the
                    # specific table, and there's no way of knowing if the
                    # caption is for a table immediately following or
                    # immediately prior. Add a little styling to make it more
                    # obvious, and some accessibility helpers.
                    chapter.content += u'<p {style}><span class="sr-only">Table caption</span>{text}</p>'.format(
                        style=fstyling,
                        text=text,
                    )
                elif role == 'heading':
                    if int(block['heading']) > 1:
                        # Heading >1. Format as heading but don't make new chapter.
                        chapter.content += u'<h{level}>{text}</h{level}>'.format(
                            level=block['heading'], text=text
                        )
                    else:
                        # Heading 1. Begin the new chapter
                        chapter_no += 1
                        chapter = self.make_chapter(text, chapter_no)
                        chapter.content = u'<h{level}>{text}</h{level}>'.format(
                            level=block['heading'], text=text
                        )
                else:
                    # Regular or other text block. Add its heading to the
                    # chapter content. In theory a table of contents could get
                    # parsed for page numbers and turned into a hyperlinked
                    # nav toc pointing to page elements, but relying on headers
                    # is probably more reliable.
                    chapter.content += u'<p {style}>{text}</p>'.format(
                        style=fstyling,
                        text=text,
                    )
            elif block['type'] == 'Page':
                chapter.add_pageref(str(block['text']))
            elif block['type'] == 'Picture':
                # Image
                content = self.make_image(block)
                if content:
                    chapter.content += content
            elif block['type'] == 'Separator' or block['type'] == 'SeparatorsBox':
                # Separator blocks seem to be fairly randomly applied and don't
                # correspond to anything useful in the original content
                pass
            elif block['type'] == 'Table':
                chapter.content += u'<table>'
            elif block['type'] == 'TableRow':
                chapter.content += u'<tr>'
                if 'last_table_elem' in block:
                    self.last_row = True
            elif block['type'] == 'TableCell':
                chapter.content += u'<td>'
                if 'last_table_elem' in block:
                    self.last_cell = True
            elif block['type'] == 'TableText':
                chapter.content += u'<p {style}>{text}</p>'.format(
                    style=fstyling,
                    text=block['text'],
                )
                if 'last_table_elem' in block:
                    chapter.content += u'</td>'
                    if self.last_cell:
                        chapter.content + u'</tr>'
                        self.last_cell = False
                        if self.last_row:
                            chapter.content += u'</table>'
                            self.last_row = False
            else:
                self.logger.debug("Ignoring Block:\n Type: {}\n Attribs: {}".format(
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
            self.blocks,
            debug=self.debug,
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

        # get the finereader version
        if 'fr-version' in self.metadata:
            self.version = self.metadata['fr-version']

        # make the HTML chapters
        self.craft_html()

        # Set the book's cover
        self.book.set_cover('images/cover.png', open(self.cover_img, 'rb').read())
        cover = self.book.items[-1]
        cover.add_link(
            href='style/style.css', rel='stylesheet', type='text/css'
        )

        # Set the book's metadata
        self.book.set_identifier(self.metadata['identifier'][0])
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
        if 'identifier-access' in self.metadata:
            for identifier_access in self.metadata['identifier-access']:
                self.book.add_metadata('DC', 'identifier', 'Access URL: {}'.format(identifier_access))
        if 'identifier-ark' in self.metadata:
            for identifier_ark in self.metadata['identifier-ark']:
                self.book.add_metadata('DC', 'identifier', 'urn:ark:{}'.format(identifier_ark))
        if 'isbn' in self.metadata:
            for isbn in self.metadata['isbn']:
                self.book.add_metadata('DC', 'identifier', 'urn:isbn:{}'.format(isbn))
        if 'oclc-id' in self.metadata:
            for oclc_id in self.metadata['oclc-id']:
                self.book.add_metadata('DC', 'identifier', 'urn:oclc:{}'.format(oclc_id))
        if 'external-identifier' in self.metadata:
            for external_identifier in self.metadata['external-identifier']:
                self.book.add_metadata('DC', 'identifier', external_identifier)
        if 'related-external-id' in self.metadata:
            for related_external_id in self.metadata['related-external-id']:
                self.book.add_metadata('DC', 'identifier', related_external_id)
        if 'subject' in self.metadata:
            for subject in self.metadata['subject']:
                self.book.add_metadata('DC', 'subject', subject)
        if 'date' in self.metadata:
            for date in self.metadata['date']:
                self.book.add_metadata('DC', 'date', date)

        # set the accessibility metadata
        self.create_accessibility_metadata()
        # Navigation for EPUB 3 & EPUB 2 fallback
        self.book.toc = self.chapters
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        # cover_ncx hack to work around Adobe Digital Editions problem
        self.book.spine = ['cover', 'nav', ] + self.chapters

        # define CSS style
        style = """.center {text-align: center}
                .sr-only {
                    position: absolute;
                    width: 1px;
                    height: 1px;
                    padding: 0;
                    margin: -1px;
                    overflow: hidden;
                    clip: rect(0,0,0,0);
                    border: 0;
                }
                .strong {font-weight: bold;}
                .italic {font-style: italic;}
                .serif {font-family: serif;}
                .sans {font-family: sans-serif;}
                img {
                    padding: 0;
                    margin: 0;
                    max-width: 100%;
                    max-height: 100%;
                    column-count: 1;
                    break-inside: avoid;
                    oeb-column-number: 1;
                }
                """
        css_file = epub.EpubItem(
            uid="style_nav",
            file_name="style/style.css",
            media_type="text/css",
            content=style
        )
        self.book.add_item(css_file)

        epub_filename = '{base}/{base}.epub'.format(base=self.base)
        epub.write_epub(epub_filename, self.book, {})

        # run checks
        verifier = EpubVerify(self.debug)
        if 'epubcheck' in self.args:
            self.logger.info("Running EpubCheck on {}".format(epub_filename))
            verifier.run_epubcheck(epub_filename)
        if 'ace' in self.args:
            self.logger.info("Running DAISY Ace on {}".format(epub_filename))
            verifier.run_ace(epub_filename)

        # clean up
        # ebooklib doesn't clean up cleanly without reset, causing problems on
        # consecutive runs
        self.tmpdir.cleanup()
        self.book.reset()
