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

from ebooklib import utils as ebooklibutils
from lxml import etree

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

    And ABBYY document begins with a font and style information:

    .. code:: html

        <documentData>
          <paragraphStyles>
            <paragraphStyle
              id="{idnum}" name="stylename"
              mainFontStyleId="{idnum}" [style info]>
            <fontStyle id="{idnum}" [style info]>
          </paragraphStyle>
          [more styles]
        </documentData>

    This is followed by the data for the pages.

    .. code:: html

        <page>
            <block></block>
            [more blocks]
        </page>


    Blocks have types. We process types Text, Picture, and Table.

    Text:

    .. code:: html

        <page>
                <region>
                <text> contains a '\\n' as a text element
                <par> The paragraph, repeatable
                    <line> The line, repeatable
                        <formatting>
                        <charParams>: The individual character

    Picture: we know the corresponding scan (page) number, & coordinates.

    Table:

    .. code:: html

            <row>
              <cell>
                <text>
                  <par>

    Each `<par>` has an identifier, which has a unique style, including
    the paragraph's role, eg:

    .. code:: html

                <par align="Right" lineSpacing="1790"
                    style="{000000DD-016F-0A36-032F-EEBBD9B8571E}">


    This corresponds to a paragraphStyle from the `<documentData>` element:

    .. code:: html

                <paragraphStyle
                    id="{000000DD-016F-0A36-032F-EEBBD9B8571E}"
                    name="Heading #1|1"
                    mainFontStyleId="{000000DE-016F-0A37-032F-176E5F6405F5}"
                    role="heading" roleLevel="1"
                    [style information]>

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
        self.page_no = 0

        # Save page numbers only if using a supporting version of ebooklib
        if 'create_pagebreak' in dir(ebooklibutils):
            self.metadata['PAGES_SUPPORT'] = True
        else:
            self.metadata['PAGES_SUPPORT'] = False

    def is_block_type(self, blockattr, blocktype):
        """ Identifies if a block has the given type. """
        if 'blockType' in blockattr and blockattr['blockType'] == blocktype:
            return True
        else:
            return False

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

        # if the language isn't explicitly set, assume English
        if 'language' not in self.metadata:
            self.metadata['language'] = 'eng'

    def parse_abbyy(self):
        """
        Parse the ABBYY into a format useful for `create_epub`. Process the
        the elements we will need to construct the EPUB: `paragraphStyle`,
        `fontStyle`, and `page`.  We traverse the entire tree twice with
        `iterparse`, because lxml builds the whole node tree in memory for even
        tag-selective `iterparse`, & if we don't traverse the whole tree, we
        can't delete the unowned nodes. `fast_iter` makes the process speedy,
        and the dual processing saves on memory. Because of the layout
        of the elements in the ABBYY file, it's too complex to do this in a
        single iterative pass.
        """

        # some basic initialization
        self.metadata['pics_by_page'] = dict()
        self.fontStyles = dict()
        self.pages = []

        # Be aggressive with garbage collection; parsing the XML hogs memory
        gc.set_threshold(1, 1, 1)

        # Get the namespace & the FR version, so we can find the other elements
        self.find_namespace()

        # paragraphStyle is a prerequisite for page
        context = etree.iterparse(
            self.document,
            events=('end',),
        )
        fast_iter(context, self.process_styles)
        del context

        # Because of the processing order of XML events, it's efficient
        # to collect para and font styles upfront & collate it after.
        for id, attribs in self.paragraphs.items():
            if (
                'mainFontStyleId' in attribs and
                'mainFontStyleId' in self.fontStyles
            ):
                    self.paragraphs[id]['fontstyle'] = self.fontStyles[
                        'mainFontStyleId'
                    ]

        # parse the metadata document next
        self.parse_metadata()

        # finally, extract the individual page elements from the XML
        context = etree.iterparse(
            self.document,
            events=('end',),
            tag="{{{}}}page".format(self.ns),
        )
        fast_iter(context, self.process_pages)
        del context

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
        Iteratively parse styles from the ABBYY file into data structures.
        The ABBYY seems to be sometimes inconsistent about whether these
        elements have a namespace, so be forgiving.
        """

        if (
            elem.tag == "{{{}}}paragraphStyle".format(self.ns) or
            elem.tag == "paragraphStyle"
        ):
            """
            Paragraph styles are on their own at the start of the ABBYY
            and contain child fontStyle elements
            """
            self.paragraphs[elem.get("id")] = dict(elem.attrib)
            fontstyles = elem.iterchildren()
            for fontstyle in fontstyles:
                self.fontStyles[fontstyle.get("id")] = dict(fontstyle.attrib)

    def process_pages(self, elem):
        """
        Iteratively process pages from the ABBYY file. We have to process now
        rather than copying the pages for later processing, because deepcopying
        an lxml element replicates the entire tree.
        The ABBYY seems to be sometimes inconsistent about whether these
        elements have a namespace, so be forgiving.
        """

        if (
            elem.tag == "{{{}}}page".format(self.ns) or
            elem.tag == "page"
        ):
            self.pagewidth = elem.get('width')
            self.pageheight = elem.get('height')
            block_per_page = elem.iterchildren()
            if not block_per_page:
                self.page_no += 1
                return
            self.newpage = True

            # Most pages have multiple `<block>` elements
            for block in block_per_page:
                self.parse_block(block)

            # Mark up the last text block on the page, if there is one
            add_last_text(self.blocks, self.page_no)

            # For accessibility, create a page number at the end of every page
            # with content.
            if (
                self.metadata['PAGES_SUPPORT'] and
                self.blocks[-1]['type'] != 'Page'
            ):
                self.blocks.append({
                    'type': 'Page',
                    'text': self.page_no,
                })

            # Set up the next iteration.
            self.page_no += 1

    def parse_block(self, block):
        """ Parse a single block on the page.  """
        blockattr = block.attrib
        blockattr['pagewidth'] = self.pagewidth
        blockattr['pageheight'] = self.pageheight
        if self.is_block_type(blockattr, "Text"):
            paras = block.iterdescendants(
                tag="{{{}}}par".format(self.ns)
            )
            # Some blocks can have multiple styles in them. We'll treat
            # those as multiple blocks.
            for para in paras:
                # Get the paragraph style and text
                para_id = para.get("style")
                if para_id not in self.paragraphs:
                    self.logger.debug(
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
                self.blocks.append({
                    'type': 'Text',
                    'page_no': self.page_no,
                    'text': sanitize_xml(text).replace('¬\n', ''),
                    'role': role,
                    'style': self.paragraphs[para_id],
                })

                # To help with unmarked header recognition
                if self.newpage:
                    self.blocks[-1]['first'] = True
                    self.newpage = False

                # Mark up heading level
                if role == 'heading':
                    level = self.paragraphs[para_id]['roleLevel']
                    # shortcut so we need fewer lookups later
                    self.blocks[-1]['heading'] = level

                para.clear()  # garbage collection
            del paras         # garbage collection

        elif self.is_block_type(blockattr, "Table"):
            # We'll process the table by treating each of its cells'
            # subordinate blocks as separate. Keep track of which  is the last
            # element in a cell/row/table, so we can close the elements after
            # each is complete.
            this_row = 1
            self.blocks.append({
                'type': 'Table',
                'style': blockattr,
                'page_no': self.page_no,
            })
            # Make the iterator into a list so we can calculate length
            # with only one iteration. Should be a small chunk so unlikely
            # to be a memory hog.
            rows = list(
                block.iterdescendants(tag="{{{}}}row".format(self.ns))
            )
            rows_in_table = len(rows)
            for row in rows:
                this_cell = 1
                self.blocks.append({
                    'type': 'TableRow',
                    'style': blockattr,
                    'page_no': self.page_no,
                })
                if this_row == rows_in_table:
                    self.blocks[-1]['last_table_elem'] = True
                this_row += 1
                cells = list(row.iterdescendants(
                    tag="{{{}}}cell".format(self.ns)
                ))
                cells_in_row = len(cells)
                for cell in cells:
                    this_contents = 1
                    self.blocks.append({
                        'type': 'TableCell',
                        'style': blockattr,
                        'page_no': self.page_no,
                    })
                    if this_cell == cells_in_row:
                        self.blocks[-1]['last_table_elem'] = True
                    this_cell += 1
                    # Parsing a cell is not quite like parsing text.
                    # The element layout is cell -> text -> par.
                    text = cell.find("a:text", namespaces=self.nsm)
                    paras = list(text.iterdescendants(
                        tag="{{{}}}par".format(self.ns)
                    ))
                    paras_in_cell = len(paras)
                    for para in paras:
                        para_id = para.get("style")
                        text = gettext(para).strip()
                        # Ignore whitespace-only para unless it's
                        # an empty cell. If so, placeholder
                        if not text and paras_in_cell > 1:
                            continue
                        self.blocks.append({
                            'type': 'TableText',
                            'style': blockattr,
                            'page_no': self.page_no,
                            'text': sanitize_xml(text),
                        })
                        if this_contents == paras_in_cell:
                            self.blocks[-1]['last_table_elem'] = True
                        this_contents += 1
                        if self.newpage:
                            self.newpage = False
                        para.clear()
                    del paras
                    del text
                    cell.clear()        # garbage collection
                del cells               # garbage collection
                row.clear()             # garbage collection
            del rows                    # garbage collection
        else:
            # Create entry for non-text blocks with type & attributes
            d = {
                'type': block.get("blockType"),
                'style': blockattr,
                'page_no': self.page_no,
            }
            self.blocks.append(d)

            # If this is an image, add it to a dict of all images
            # by page number, so we can strip out overlapping images
            if self.is_block_type(blockattr, "Picture"):
                if self.page_no in self.metadata['pics_by_page']:
                    self.metadata['pics_by_page'].append(d)
                else:
                    self.metadata['pics_by_page'] = [d, ]

            d = dict()
