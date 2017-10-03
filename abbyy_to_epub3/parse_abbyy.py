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


logger = logging.getLogger(__name__)


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
    <page>
        <block>: types Picture, Separator, Table, or Text
            Text:
            <region>
            <text> contains a '\n' as a text element
               <par>: The paragraph, repeatable
                <line>: The line, repeatable
                    <formatting>
                       <charParams>: The individual character
            Image:
            Separator:
            Table:

            Each paragraph has identifier, which has a unique style, including
               the paragraph's role, eg:
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
    """

    # Set these once we start parsing the tree and know our schema
    ns = ''
    nsm = ''
    version = ''
    etree = ''

    def __init__(self, document, metadata_file, metadata, paragraphs, blocks):
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

    def is_text_block(self, elem):
        """ Identifies if an XML element is a textblock. """
        if (
            elem.tag == "{{{}}}block".format(self.ns) and
            elem.get("blockType") == "Text"
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
        logger.debug("Version {}".format(self.version))

        self.parse_metadata()
        self.parse_paragraph_styles()
        self.parse_content()

    def parse_paragraph_styles(self):
        """ Paragraph styles are in their own elements at the start of the text """
        styles = self.tree.findall(".//a:paragraphStyle", namespaces=self.nsm)
        for style in styles:
            id = style.get("id")
            self.paragraphs[id] = style.attrib

    def parse_content(self):
        """ Parse each page of the book.  """
        page_no = 1
        block_dict = {'page_no': page_no}

        pages = self.tree.findall(".//a:page", namespaces=self.nsm)

        pages.pop(0)    # ignore the calibration page
        for page in pages:
            block_per_page = page.getchildren()
            if not block_per_page:
                page_no += 1
                continue

            newpage = True

            for block in block_per_page:
                if self.is_text_block(block):
                    paras = block.findall(".//a:par", namespaces=self.nsm)
                    # Some blocks can have multiple styles in them. We'll treat
                    # those as multiple blocks.
                    for para in paras:
                        para_id = para.get("style")
                        text = gettext(para).strip()
                        if not text:
                            # Ignore whitespace-only pars
                            continue
                        block_dict['type'] = 'Text'
                        if newpage:
                            block_dict['first'] = True
                            newpage = False
                        if (
                            # FR6 docs have no structure, styles, roles
                            self.version == "FR10" and
                            self.paragraphs[para_id]['role'] == "heading"
                           ):
                            level = self.paragraphs[para_id]['roleLevel']
                            # shortcut so we need fewer lookups later
                            block_dict['heading'] = level
                            block_dict['text'] = sanitize_xml(text)
                        else:
                            block_dict['text'] = sanitize_xml(text)

                        self.blocks.append(block_dict)
                        block_dict = {'page_no': page_no}
                else:
                    # Create an entry for non-text blocks with type & attributes
                    block_dict['type'] = block.get("blockType")
                    block_dict['style'] = block.attrib
                    self.blocks.append(block_dict)

                # Clean out the placeholder dict before the next loop
                block_dict = {'page_no': page_no}

            # Add the block to our list
            self.blocks.append(block_dict)

            # Mark up the last text block on the page, if there is one
            add_last_text(self.blocks, page_no)

            # For accessibility, create a page number at the end of every page
            if self.PAGES_SUPPORT:
                block_dict = {
                    'type': 'Page',
                    'text': page_no,
                }
                self.blocks.append(block_dict)

            # Set up the next iteration.
            page_no += 1
            block_dict = {'page_no': page_no}

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
