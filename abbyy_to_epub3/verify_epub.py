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

import json
import logging
import subprocess

from distutils.version import LooseVersion
from epubcheck import EpubCheck
from pprint import pformat


class EpubVerify(object):
    """
    Provides tools for verifying the quality of the EPUB,
    using common libraries such as EPUBcheck.
    Where sensible, provides tools for automatically parsing the output.
    """

    def __init__(self, debug=False):
        self.logger = logging.getLogger(__name__)
        self.debug = debug
        if self.debug:
            self.logger.addHandler(logging.StreamHandler())
            self.logger.setLevel(logging.DEBUG)

        self.results = {}

    def run_epubcheck(self, epub):
        """ Runs epubcheck and stores the output. """
        result = EpubCheck(epub)
        self.results['epubcheck'] = result

        if self.debug:
            if result.valid:
                self.logger.info("EpubCheck passed")
            else:
                self.logger.info("EpubCheck failed")
                print("EpubCheck result: {}\n{}".format(
                    result.valid,
                    pformat(result.messages),
                ))

        return result

    def run_ace(self, epub, tmpdir):
        """
        Runs DAISY Ace and stores the output.
        Ace creates a JSON report in [dir]/report.json
        """

        # Many OSs ship with older versions of NodeJS, which can cause Ace
        # to fail silently. Do a version check!
        try:
            version_check = subprocess.Popen(
                ['node', '--version'], stdout=subprocess.PIPE,
            )
        except FileNotFoundError as e:
            # Don't raise an exception, but log the error
            self.logger.error("Node not present, but required for Ace:", e)
            return
        vers, _ = version_check.communicate()
        vers_string = vers.decode("utf-8").rstrip()
        if LooseVersion(vers_string) <= LooseVersion('v6.4.0'):
            # Don't raise an exception, but log the error
            self.logger.error("Node is {}, must be at least v6.4.0")
            return

        # Run the Ace checker
        outdir = tmpdir + '/ace_results'
        cmd = [
            "ace",
            "--outdir", outdir,
            "--silent",
            epub,
           ]
        try:
            exit_code = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
            )
        except FileNotFoundError as e:
            # Don't raise an exception, but log the error
            self.logger.error("DAISY Ace is not installed correctly:", e)
            return
        with open(outdir + '/report.json') as f:
            result = json.load(f)
        self.results['ace'] = result

        # In order for failures to be reported, an Ace configuration file
        # must exist with `return-2-on-validation-error` set to true.
        # See https://daisy.github.io/ace/docs/config/
        if exit_code.returncode != 2:
            self.logger.debug("DAISY Ace passed")
            ace_passed = True
        else:
            self.logger.debug("DAISY Ace found errors")
            ace_passed = False
        return result, ace_passed
