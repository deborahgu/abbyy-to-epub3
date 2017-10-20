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

import logging
from epubcheck import EpubCheck
from pprint import pformat


class EpubVerify(object):
    """
    Provides tools for verifying the quality of the EPUB,
    using common libraries such as EPUBcheck and DAISY Ace.
    Where sensible, provides tools for automatically parsing the output.
    """

    def __init__(self, debug=False):
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.addHandler(logging.StreamHandler())
            self.logger.setLevel(logging.DEBUG)

        self.results = {}

    def run_epubcheck(self, epub):
        """ Runs epubcheck and stores the output. """
        result = EpubCheck(epub)
        self.results['epubcheck'] = result

        if result.valid:
            self.logger.info("EpubCheck passed")
        else:
            self.logger.info("EpubCheck failed")
            print("EpubCheck result: {}\n{}".format(
                result.valid,
                pformat(result.messages),
            ))

        return result
