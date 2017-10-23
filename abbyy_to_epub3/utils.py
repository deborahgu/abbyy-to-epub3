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
