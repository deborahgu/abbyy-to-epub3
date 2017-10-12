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
from lxml import etree

import logging
import sys

from abbyy_to_epub3 import constants


def gettext(elem):
    text = elem.text or ""
    for e in elem:
        text += gettext(e)
        if e.tail:
            text += e.tail.strip()
    return text


def sanitize_xml(text):
    """ Removes forbidden entities from any XML string """
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def add_last_text(blocks, page):
    """
    Given a list of blocks and the page number of the last page in the list,
    mark up the last text block for that page in the list, if it exists.
    """
    elem = blocks[-1]
    if 'page_no' not in elem:
        # On a page_no element, so at end of previous page
        return
    if elem['page_no'] == page:
        if 'type' in elem and elem['type'] == 'text':
            elem['last'] = True
        elif len(blocks) > 1:
            add_last_text(blocks[:-1], page)


class AbbyyParser(object):
    """
    The ABBYY parser object.
    Parses ABBYY metadata in preparation for import into an EPUB 3 document.

    Here are the components of the ABBYY schema we use:

    .. code:: html

    <page>
        <block>types Picture, Separator, Table, or Text</block>

    Text:

    .. code:: html

    <page>
            <region>
            <text> contains a '\\n' as a text element
               <par> The paragraph, repeatable
                <line> The line, repeatable
                    <formatting>
                       <charParams>: The individual character

    Image:
    Separator:
    Table:

    .. code:: html

            <row>
              <cell>
                <text>
                  <par>

    Each paragraph has an identifier, which has a unique style, including
    the paragraph's role, eg:

    .. code:: html

                <paragraphStyle
                    id="{000000DD-016F-0A36-032F-EEBBD9B8571E}"
                    name="Heading #1|1"
                    mainFontStyleId="{000000DE-016F-0A37-032F-176E5F6405F5}"
                    role="heading"
                    roleLevel="1"
                    align="Right"
                    startIndent="0" leftIndent="0"
                    rightIndent="0" lineSpacing="1790" fixedLineSpacing="1">
               <par align="Right" lineSpacing="1790"
                    style="{000000DD-016F-0A36-032F-EEBBD9B8571E}">

    The roles map as follows:

    =================   ==============
    Role name           role
    =================   ==============
    Body text   		text
    Footnote    		footnote
    Header or footer	rt
    Heading     		heading
    Other	        	other
    Table caption		tableCaption
    Table of contents	contents
    =================   ==============

    """

    # Set these once we start parsing the tree and know our schema
    ns = ''
    nsm = ''
    version = ''
    etree = ''

    def __init__(self, document, metadata_file, metadata, paragraphs, blocks, debug=False):
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.addHandler(logging.StreamHandler())
            self.logger.setLevel(logging.DEBUG)

        self.document = document
        self.metadata_file = metadata_file
        self.metadata = metadata
        self.paragraphs = paragraphs
        self.blocks = blocks

        # Save page numbers only if using a supporting version of ebooklib
        if hasattr(epub.EpubHtml, 'add_pageref'):
            self.PAGES_SUPPORT = True
        else:
            self.PAGES_SUPPORT = False

    def is_block_type(self, elem, blocktype):
        """ Identifies if an XML element is a textblock. """
        if (
            elem.tag == "{{{}}}block".format(self.ns) and
            elem.get("blockType") == blocktype
           ):
            return True
        else:
            return False

    def parse_abbyy(self):
        """ read the ABBYY file into an lxml etree """
        self.tree = etree.parse(self.document)

        # We can parse FR6 schema, a little
        abbyy_nsm = self.tree.getroot().nsmap
        if constants.ABBYY_NS in abbyy_nsm.values():
            self.nsm = constants.ABBYY_NSM
            self.ns = constants.ABBYY_NS
            self.version = "FR10"
        elif constants.OLD_NS in abbyy_nsm.values():
            self.nsm = constants.OLD_NSM
            self.ns = constants.OLD_NS
            self.version = "FR6"
        else:
            raise RuntimeError("Input XML document is not a supported schema.")
        self.logger.debug("Version {}".format(self.version))
        self.metadata['fr-version'] = self.version
        self.metadata['pics_by_page'] = dict()

        self.parse_metadata()
        self.parse_paragraph_styles()
        self.parse_content()

    def parse_paragraph_styles(self):
        """ Paragraph styles are in their own elements at the start of the text """
        styles = self.tree.findall(".//a:paragraphStyle", namespaces=self.nsm)
        fontstyles = self.tree.findall(".//a:fontStyle", namespaces=self.nsm)
        for style in styles:
            id = style.get("id")
            self.paragraphs[id] = dict(style.attrib)
            if 'mainFontStyleId' in style.attrib:
                for fstyle in fontstyles:
                    font = fstyle.get("id")
                    if font == style.attrib['mainFontStyleId']:
                        break
                self.paragraphs[id]['fontstyle'] = dict(fstyle.attrib)

    def make_para_blocks(self, elem):
        """
        Given an text node ElementTree, make blocks for all children and
        add them to the list of blocks
        """
        pass

    def parse_content(self):
        """ Parse each page of the book.  """
        page_no = 1
        d = {'page_no': page_no}

        pages = self.tree.findall(".//a:page", namespaces=self.nsm)

        pages.pop(0)    # ignore the calibration page
        for page in pages:
            block_per_page = page.getchildren()
            if not block_per_page:
                page_no += 1
                continue

            newpage = True

            for block in block_per_page:
                if self.is_block_type(block, "Text"):
                    paras = block.findall(".//a:par", namespaces=self.nsm)
                    # Some blocks can have multiple styles in them. We'll treat
                    # those as multiple blocks.
                    for para in paras:
                        # Get the paragraph style and text
                        para_id = para.get("style")
                        text = gettext(para).strip()

                        # Ignore whitespace-only pars
                        if not text:
                            continue

                        # Get the paragraph role
                        # FR6 docs have no structure, styles, roles
                        if self.version == "FR10":
                            role = self.paragraphs[para_id]['role']
                        else:
                            role = "FR6"

                        # Skip headers and footers
                        if role == 'rt':
                            continue

                        # This is a good text chunk. Instantiate the block.
                        d = {
                            'type': 'Text',
                            'page_no': page_no,
                            'text': sanitize_xml(text),
                            'role': role,
                            'style': self.paragraphs[para_id]
                        }

                        # To help with unmarked header recognition
                        if newpage:
                            d['first'] = True
                            newpage = False

                        # Mark up heading level
                        if role == 'heading':
                            level = self.paragraphs[para_id]['roleLevel']
                            # shortcut so we need fewer lookups later
                            d['heading'] = level

                        # Whenever you append to the list, re-instantiate
                        self.blocks.append(d)
                        d = dict()

                elif self.is_block_type(block, "Table"):
                    # We'll process the table by treating each of its cells
                    # subordinate blocks as separate. Keep track of which
                    # is the last element in a cell/row/table, so we can
                    # close the elements after each is complete.
                    this_row = 1
                    d = {
                        'type': 'Table',
                        'style': block.attrib,
                        'page_no': page_no,
                    }
                    self.blocks.append(d)
                    d = dict()
                    rows = block.findall(".//a:row", namespaces=self.nsm)
                    rows_in_table = len(rows)
                    for row in rows:
                        this_cell = 1
                        d = {
                            'type': 'TableRow',
                            'style': block.attrib,
                            'page_no': page_no,
                        }
                        if this_row == rows_in_table:
                            d['last_table_elem'] = True
                        this_row += 1
                        self.blocks.append(d)
                        d = dict()
                        cells = row.findall("a:cell", namespaces=self.nsm)
                        cells_in_row = len(cells)
                        for cell in cells:
                            this_contents = 1
                            d = {
                                'type': 'TableCell',
                                'style': block.attrib,
                                'page_no': page_no,
                            }
                            if this_cell == cells_in_row:
                                d['last_table_elem'] = True
                            this_cell += 1
                            self.blocks.append(d)
                            d = dict()
                            # Parsing a cell is not quite like parsing regular
                            # text.
                            # The layout is cell -> text -> par.
                            text = cell.find("a:text", namespaces=self.nsm)
                            paras = text.findall("a:par", namespaces=self.nsm)
                            paras_in_cell = len(paras)
                            for para in paras:
                                para_id = para.get("style")
                                text = gettext(para).strip()
                                # Ignore whitespace-only para unless it's
                                # an empty cell. If so, placeholder
                                if not text and len(paras) > 1:
                                    continue
                                d = {
                                    'type': 'TableText',
                                    'style': block.attrib,
                                    'page_no': page_no,
                                    'text': sanitize_xml(text),
                                }
                                if this_contents == paras_in_cell:
                                    d['last_table_elem'] = True
                                this_contents += 1
                                self.blocks.append(d)
                                d = dict()
                                if newpage:
                                    newpage = False
                else:
                    # Create an entry for non-text blocks with type & attributes
                    d = {
                        'type': block.get("blockType"),
                        'style': block.attrib,
                        'page_no': page_no,
                    }
                    self.blocks.append(d)

                    # If this is an image, add it to a dict of all images
                    # by page number, so we can strip out overlapping images
                    if self.is_block_type(block, "Picture"):
                        if page_no in self.metadata['pics_by_page']:
                            self.metadata['pics_by_page'].append(d)
                        else:
                            self.metadata['pics_by_page'] = [d, ]

                    d = dict()

            # Mark up the last text block on the page, if there is one
            add_last_text(self.blocks, page_no)

            # For accessibility, create a page number at the end of every page
            if self.PAGES_SUPPORT:
                d = {
                    'type': 'Page',
                    'text': page_no,
                }
                self.blocks.append(d)
                d = dict()

            # Set up the next iteration.
            page_no += 1

    def parse_metadata(self):
        """
        Parse out the metadata from the _meta.xml file
        """
        tree = etree.parse(self.metadata_file)
        root = tree.getroot()
        terms = root.iterchildren()

        for term in terms:
            if term.tag in self.metadata:
                self.metadata[term.tag].append(term.text)
            else:
                self.metadata[term.tag] = [term.text, ]
