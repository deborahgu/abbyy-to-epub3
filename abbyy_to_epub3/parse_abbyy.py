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

import sys

from abbyy_to_epub3.constants import ABBYY_NS as ns
from abbyy_to_epub3.constants import ABBYY_NSM as nsm

"""
Parses the ABBYY metadata in preparation for import into an EPUB 3 document

Here are the components of the ABBYY schema we use:
<page>
    <block>: types Picture, Separator, Table, or Text
        Text:
        <region>
        <text> contains a '\n' as a text element
           <par>: The paragraph
            <line>: The line
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

def gettext(elem):
    text = elem.text or ""
    for e in elem:
        text+= gettext(e)
        if e.tail:
            text += e.tail.strip()
    return text


def is_text_block(elem):
    """ Identifies if an XML element is a textblock. """
    if (elem.tag == "{{{}}}block".format(ns) and
        elem.get("blockType") == "Text"):
         return True
    else:
        return False

def parse_abbyy(document, metadata_file, metadata, paragraphs, blocks):
    """ read the ABBYY file into an lxml etree """
    tree = etree.parse(document)

    parse_metadata(metadata_file, metadata)
    parse_paragraph_styles(tree, paragraphs)
    parse_content(tree, paragraphs, blocks)

def parse_paragraph_styles(tree, paragraphs):
    """ Paragraph styles are in their own elements at the start of the text """
    styles = tree.findall(".//a:paragraphStyle", namespaces=nsm)
    for style in styles:
        id = style.get("id")
        paragraphs[id] = style.attrib


def parse_content(tree, paragraphs, blocks):
    """ Parse each page of the book.  """
    page_no = 0
    block_dict = {}

    pages = tree.findall(".//a:page", namespaces=nsm)
    for page in pages:
        page_no += 1

        block_per_page = page.getchildren()
        for block in block_per_page:
            block_dict['page_no'] = page_no
            if is_text_block(block):
                para = block.find(".//a:par", namespaces=nsm)
                para_id = para.get("style")
                text = gettext(block).strip()
                block_dict['type'] = 'Text'
                if paragraphs[para_id]['role'] == "heading":
                    level = paragraphs[para_id]['roleLevel']
                    # shortcut so we need fewer lookups later
                    block_dict['heading'] = level
                    block_dict['text'] = text
                else:
                    block_dict['text'] = text
            else:
                # Create an entry for non-text blocks with type & attributes
                block_dict['type'] = block.get("blockType")
                block_dict['style'] = block.attrib
            blocks.append(block_dict)

            # Clean out the placeholder dict before the next loop
            block_dict = {}

        # For a11y, add a visually available page number after every page
        block_dict['type'] = 'Text'
        block_dict['text'] = u'<div class="center"><span epub:type="pagebreak" title="{page_no}" id="Page_{page_no}">Page {page_no}</span></div>'.format(page_no=page_no)
        block_dict['page_no'] = page_no
        blocks.append(block_dict)
        block_dict = {}

def parse_metadata(metadata_file, metadata):
    """
    Parse out the metadata from the _meta.xml file
    """
    tree = etree.parse(metadata_file)
    root = tree.getroot()
    terms = root.iterchildren()

    for term in terms:
        if term.tag in metadata:
            metadata[term.tag].append(term.text)
        else:
            metadata[term.tag] = [term.text,]
