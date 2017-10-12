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
