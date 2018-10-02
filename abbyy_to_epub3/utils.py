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


def is_increasing(l):
    """
    Given a list, return True if the list elements are monotonically
    increasing, and False otherwise.
    """
    for a, b in zip(l, l[1:]):
        if a >= b:
            return False
    return True


def dirtify_xml(text):
    """
    Re-adds forbidden entities to any XML string.
    Could cause problems in the unlikely event the string literally should be
    '&amp'
    """
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace('"', "&quot;")
    text = text.replace("&apos;", "'")
    return text


def sanitize_xml(text):
    """ Removes forbidden entities from any XML string """
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def gettext(elem):
    """
    Given an element, get all text from within element and its children.
    Strips out file artifact whitespace (unlike etree.itertext).
    """
    text = elem.text or ""
    for e in elem:
        text += gettext(e)
        if e.tail:
            text += e.tail.strip()
    return text


def fast_iter(context, func):
    """
    Garbage collect as you iterate to save memory
    Based on StackOverflow modification of Liza Daly's fast_iter
    """
    for event, elem in context:
        # make sure your function processes any necessary descendants
        func(elem)
        elem.clear()
        # Also eliminate now-empty references from the root node to elem
        for ancestor in elem.xpath('ancestor-or-self::*'):
            while ancestor.getprevious() is not None:
                del ancestor.getparent()[0]
    del context
