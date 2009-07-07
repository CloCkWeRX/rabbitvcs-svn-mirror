from __future__ import absolute_import 

import locale

def initialize_locale():
    _locale, encoding = locale.getdefaultlocale()
    if _locale is None:
        _locale = "en_US"
    if encoding is None:
        encoding = "utf8"
        
    locale.setlocale(locale.LC_ALL, (_locale, encoding))
