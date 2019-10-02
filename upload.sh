#!/bin/bash

# Only works within IA's network.
# Make sure to bump version # in __init__.py prior to running

pip3 install devpi-client
devpi use https://devpi.archive.org/
devpi login books
devpi use books/formats
devpi upload
pip3 install --upgrade -i https://devpi.archive.org/books/formats abbyy_to_epub3
