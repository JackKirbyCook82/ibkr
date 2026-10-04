# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR History Bars Objects
@author: Jack Kirby Cook
@file:   ibkr/history/bars.py

"""

from abc import ABC

from finance.enumerations import Instrument
from finance.reporting import Results
from webscraping.webpages import WebSOCKPage
from support.mixins import Logging

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["", ""]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


options_columns = ["ticker", "expire", "option", "strike", "datatime", "open", "close", "high", "low", "volume"]
stocks_columns = ["ticker", "datetime", "open", "close", "high", "low", "volume"]


class IBKRBarsHistoryPage(WebSOCKPage, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        pass


class IBKRStockBarsHistoryPage(IBKRBarsHistoryPage):
    pass

class IBKROptionBarsHistoryPage(IBKRBarsHistoryPage):
    pass


class IBKRBarsHistoryDownloader(Results, Logging, ABC):
    def __init_subclass__(cls, /, page, columns, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.Columns = columns
        cls.Page = page

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__page = type(self).Page(*args, **kwargs)
        self.__columns = list(type(self).Columns)

    def __call__(self, products, /, **kwargs):
        pass

    def downloader(self, products, /, **kwargs):
        pass

    @property
    def columns(self): return self.__columns
    @property
    def page(self): return self.__page


class IBKRStockBarsHistoryDownloader(IBKRBarsHistoryDownloader, page=IBKRStockBarsHistoryPage, columns=stocks_columns):
    def scope(self, products, **kwargs): return super().scope(products, instrument=Instrument.STOCK)


class IBKROptionBarsHistoryDownloader(IBKRBarsHistoryDownloader, page=IBKROptionBarsHistoryPage, columns=options_columns):
    def scope(self, products, **kwargs): return super().scope(products, instrument=Instrument.OPTION)






