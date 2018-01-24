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


ABBYY_NS = 'http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml'
OLD_NS = 'http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml'
ABBYY_NSM = {
    'a': ABBYY_NS,
}
OLD_NSM = {
    'a': OLD_NS,
}

# Some page types should always be skipped
skippable_pages = [
    'Cover',
    'Copyright',
    'Color Card',
    'Title',
]
