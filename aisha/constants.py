import sys

VERSION = '0.9.1'

PY3 = sys.version_info[0] == 3
if PY3:
    unicode = str
