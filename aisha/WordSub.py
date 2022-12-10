from __future__ import print_function
try: dict
except: from UserDict import UserDict as dict

import re
import string
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

class WordSub(dict):

    def _wordToRegex(self, word):
        if word != "" and word[0].isalpha() and word[-1].isalpha():
            return "\\b%s\\b" % re.escape(word)
        else:
            return r"\b%s\b" % re.escape(word)

    def _update_regex(self):
        self._regex = re.compile("|".join(map(self._wordToRegex, self.keys())))
        self._regexIsDirty = False

    def __init__(self, defaults = {}):
        self._regex = None
        self._regexIsDirty = True
        for k,v in defaults.items():
            self[k] = v

    def __call__(self, match):
        return self[match.group(0)]

    def __setitem__(self, i, y):
        self._regexIsDirty = True
        super(type(self),self).__setitem__(i.lower(),y.lower()) # key = value
        super(type(self),self).__setitem__(string.capwords(i), string.capwords(y)) # Key = Value
        super(type(self),self).__setitem__(i.upper(), y.upper()) # KEY = VALUE

    def sub(self, text):
        if self._regexIsDirty:
            self._update_regex()
        return self._regex.sub(self, text)
