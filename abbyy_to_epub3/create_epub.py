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
import os, sys
from zipfile import ZipFile

from abbyy_to_epub3.parse_abbyy import parse_abbyy

def craft_epub(document_basename):
    """ Assemble the extracted metadata & text into an EPUB  """

    # document files
    abbyy_file_zipped = "{base}/{base}_abbyy.gz".format(base=document_basename)
    abbyy_file = "{base}/{base}_abbyy".format(base=document_basename)
    images_zipped = "{base}/{base}_jp2.zip".format(base=document_basename)
    cover_file_name = "{base}_jp2/{base}_0001.jp2".format(base=document_basename)
    metadata_file = "{base}/{base}_meta.xml".format(base=document_basename)

    # unzip as necessary. 
    # Write files to disk. These might be too huge to hold in memory.
    with gzip.open(abbyy_file_zipped, 'rb') as infile:
        with open(abbyy_file, 'wb') as outfile:
            for line in infile:
                outfile.write(line)
    with ZipFile(images_zipped) as f:
        cover_file = f.extract(cover_file_name)

    # dictionaries to store the extracted data
    metadata = {}
    blocks = []     # each text or non-text block, with contents & attributes
    paragraphs = {} # paragraph style info

    book = epub.EpubBook()

    # convert our directionality abbreviation to ebooklib abbreviation
    direction = {
        'lr': 'ltr',
        'rl': 'rtl',
    }

    # convert the JP2K file into a PNG for the cover
    f, e = os.path.splitext(os.path.basename(cover_file_name))
    pngfile = f + ".png"
    try:
        Image.open(cover_file).save(pngfile)
    except IOError as e:
        print("Cannot create cover file: {}".format(e))

    # parse the ABBYY
    parse_abbyy(abbyy_file, metadata_file, metadata, paragraphs, blocks)

    # Set the metadata
    if 'page-progression' in metadata:
        progression = direction[metadata['page-progression'][0]]
    else:
        progression = 'default'

    book.set_cover('cover.png', open(pngfile, 'rb').read())
    book.set_direction(progression)
    for identifier in metadata['identifier']:
        book.set_identifier(identifier)
    for language in metadata['language']:
        book.set_language(language)
    for title in metadata['title']:
        book.set_title(title)
    for creator in metadata['creator']:
        book.add_author(creator)
    for description in metadata['description']:
        book.add_metadata('DC', 'description', description)
    for publisher in metadata['publisher']:
        book.add_metadata('DC', 'publisher', publisher)


    # Craft the EPUB sections.
    # Break sections at text elements marked role: heading,
    # Break files at any headings with roleLevel: 1
    # This will be greatly imperfect, but better than having no navigation

    # create chapter
    chapters = []
    # Default section to hold cover image & everything until the first heading
    heading = "Title"
    chapter_no = 1
    content = ""
    for block in blocks:
        if 'text' in block:
            if 'heading' not in block:
                # Regular textblock. Add its heading to the chapter content.
                content += u'<p>{}</p>'.format(block['text'])
            else:
                # A heading. Close off previous chapter & start a new one.
                # Heading. Make a new chapter.
                # FIXME:  figure out nesting
                chapter = epub.EpubHtml(
                    title=heading,
                    # pad out the filename to four digits
                    file_name='chap_{:0>4}.xhtml'.format(chapter_no),
                    lang='{}'.format(metadata['language'][0])
                )
                chapter.add_link(href='style/nav.css', rel='stylesheet', type='text/css')
                chapter.content = content
                book.add_item(chapter)
                chapters.append(chapter)
                chapter_no += 1
                # clear this out for next iteration; reset with chapter heading
                heading = block['text']
                content = u'<h{level}>{text}</h{level}>'.format(
                    level=block['heading'], text=heading
                )
        elif block['type'] == 'Separator':
            content += u'<hr />'
        else:
            # FIXME for now just print the block type is
            content += "<div style='border:5; padding: 5'>Block type {}</div>".format(block['type'])
    
    # define Table Of Contents
    book.toc = chapters
    
    # add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # define CSS style
    style = '.center {text-align: center}'
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    
    # add CSS file
    book.add_item(nav_css)
    
    # basic spine
    book.spine = ['nav'] + chapters
    

    epub.write_epub('{base}/{base}.epub'.format(base=document_basename), book, {})
