﻿# Copyright 2017 Deborah Kaplan
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

from ebooklib import utils as ebooklibutils
from lxml import etree

from copy import deepcopy
import gc
import logging

from abbyy_to_epub3 import constants
from abbyy_to_epub3.utils import fast_iter, gettext, sanitize_xml


def add_last_text(blocks, page):
    """
    Given a list of blocks and the page number of the last page in the list,
    mark up the last text block for that page in the list, if it exists.
    """
    while len(blocks) >= 1:
        # Look for a page number in the last block our list
        elem = blocks[-1]
        # If page_no isn't here, we're at end of previous page
        if 'page_no' not in elem:
            return
        # If page_no is here and matches, set elem to 'last'
        if elem['page_no'] == page:
            if 'type' in elem and elem['type'] == 'text':
                elem['last'] = True
                return
        # redo loop with the list truncated by final element
        blocks = blocks[:-1]
        continue


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
    Body text           text
    Footnote            footnote
    Header or footer    rt
    Heading             heading
    Other               other
    Table caption       tableCaption
    Table of contents   contents
    =================   ==============

    """

    # Set these once we start parsing the tree and know our schema
    ns = ''
    nsm = ''
    version = ''
    etree = ''

    def __init__(
        self, document, metadata_file, metadata,
        paragraphs, blocks, debug=False
    ):
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
        if 'create_pagebreak' in dir(ebooklibutils):
            self.metadata['PAGES_SUPPORT'] = True
        else:
            self.metadata['PAGES_SUPPORT'] = False

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
        """
        Parse the ABBYY into a format useful for create_epub
        """

        # some basic initialization
        self.metadata['pics_by_page'] = dict()
        self.fontStyles = dict()
        self.pages = []

        # Be aggressive with garbage collection; parsing the XML hogs memory
        gc.set_threshold(1, 1, 1)

        # Get the namespace & the FR version, so we can find the other elements
        self.find_namespace()

        ###
        # Now we find the elements we will need to construct the EPUB:
        # paragraphStyle, fontStyle, and page.
        # These are broken out into individual chunks after which we clean up,
        # because parsing the XML is a memory hog.
        ###

        # fontStyle is a prerequisite for getting paragraphStyle correct
        context = etree.iterparse(
            self.document,
            events=('end',),
            tag="{{{}}}fontStyle".format(self.ns),
        )
        fast_iter(context, self.decompose_xml)
        del context

        # paragraphStyle is a prerequisite for page
        context = etree.iterparse(
            self.document,
            events=('end',),
            tag="{{{}}}paragraphStyle".format(self.ns),
        )
        fast_iter(context, self.decompose_xml)
        del context

        # parse the metadata document next
        self.parse_metadata()

        # finally, extract the individual page elements from the XML
        context = etree.iterparse(
            self.document,
            events=('end',),
            tag="{{{}}}page".format(self.ns),
        )
        fast_iter(context, self.decompose_xml)
        del context

        # once we have the elements we can build our data structures
        # to create the EPUB
        self.parse_content()

        # if we don't clear the list, the page elements will stick around
        # even after the list's scope has vanished, leaking memory
        self.pages.clear()

    def find_namespace(self):
        """
        find the namespace of an XML document. Assumes that the namespace of
        the first element in the context is the namespace we need. This is more
        memory-efficient then parsing the entire tree to get the root node.
        """
        context = etree.iterparse(self.document, events=('start',),)
        for event, elem in context:
            # Namespace depends on finereader version.
            # We can parse FR6 schema, a little
            if not self.version:
                abbyy_nsm = elem.nsmap
                if constants.ABBYY_NS in abbyy_nsm.values():
                    self.nsm = constants.ABBYY_NSM
                    self.ns = constants.ABBYY_NS
                    self.version = "FR10"
                elif constants.OLD_NS in abbyy_nsm.values():
                    self.nsm = constants.OLD_NSM
                    self.ns = constants.OLD_NS
                    self.version = "FR6"
                else:
                    raise RuntimeError("Input XML not in a supported schema.")
                self.logger.debug("FineReader Version {}".format(self.version))
                self.metadata['fr-version'] = self.version
            else:
                return

    def decompose_xml(self, elem):
        """
        iteratively parse the ABBYY file into data structures
        so that intelligent parsing can happen later.
        The ABBYY seems to be sometimes inconsistent about whether these
        elements have a namespace, so be forgiving.
        """

        if (
            elem.tag == "{{{}}}fontStyle".format(self.ns) or
            elem.tag == "fontStyle"
        ):
            self.fontStyles[elem.get("id")] = dict(elem.attrib)
        elif (
            elem.tag == "{{{}}}paragraphStyle".format(self.ns) or
            elem.tag == "paragraphStyle"
        ):
            """
            Paragraph styles are on their own at the start of the ABBYY
            and refer to sibling fontStyle elements
            """
            id = elem.get("id")
            attribs = dict(elem.attrib)
            self.paragraphs[id] = attribs
            if (
                'mainFontStyleId' in attribs and
                'mainFontStyleId' in self.fontStyles
            ):
                    self.paragraphs[id]['fontstyle'] = self.fontStyles[
                        'mainFontStyleId'
                    ]

        elif (
            elem.tag == "{{{}}}page".format(self.ns) or
            elem.tag == "page"
        ):
            self.pages.append(deepcopy(elem))
        else:
            return

        # only garbage collect if we have found & processed a node
        elem.clear()

    def parse_content(self):
        """ Parse each page of the book.  """
        page_no = 1
        d = {'page_no': page_no}

        self.pages[0].clear()    # clear the memory first
        self.pages.pop(0)    # ignore the calibration page
        for page in self.pages:
            pagewidth = page.get('width')
            pageheight = page.get('height')
            block_per_page = page.getchildren()
            if not block_per_page:
                page_no += 1
                continue
            newpage = True

            for block in block_per_page:
                blockattr = block.attrib
                blockattr['pagewidth'] = pagewidth
                blockattr['pageheight'] = pageheight
                if self.is_block_type(block, "Text"):
                    paras = block.findall(".//a:par", namespaces=self.nsm)
                    # Some blocks can have multiple styles in them. We'll treat
                    # those as multiple blocks.
                    for para in paras:
                        # Get the paragraph style and text
                        para_id = para.get("style")
                        if para_id not in self.paragraphs:
                            self.logger.info(
                                'Block {} has no paragraphStyle'.format(
                                    para_id
                                )
                            )
                            self.paragraphs[para_id] = dict()
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
                        # The modern ABBYY parser is consistent in its handling
                        # of EOL hyphens, making it safe to strip them.
                        d = {
                            'type': 'Text',
                            'page_no': page_no,
                            'text': sanitize_xml(text).replace('¬\n', ''),
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

                        para.clear()  # garbage collection
                    del paras         # garbage collection

                elif self.is_block_type(block, "Table"):
                    # We'll process the table by treating each of its cells
                    # subordinate blocks as separate. Keep track of which
                    # is the last element in a cell/row/table, so we can
                    # close the elements after each is complete.
                    this_row = 1
                    d = {
                        'type': 'Table',
                        'style': blockattr,
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
                            'style': blockattr,
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
                                'style': blockattr,
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
                                    'style': blockattr,
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
                            cell.clear()        # garbage collection
                        del cells               # garbage collection
                        row.clear()             # garbage collection
                    del rows                    # garbage collection
                else:
                    # Create entry for non-text blocks with type & attributes
                    d = {
                        'type': block.get("blockType"),
                        'style': blockattr,
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
            if self.metadata['PAGES_SUPPORT']:
                d = {
                    'type': 'Page',
                    'text': page_no,
                }
                self.blocks.append(d)
                d = dict()

            # Set up the next iteration.
            page_no += 1
            page.clear()

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
