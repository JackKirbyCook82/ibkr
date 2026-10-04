# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR History Trades Objects
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
__all__ = ["IBKRStockTradesHistoryDownloader", "IBKROptionTradesHistoryDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


options_columns = ["ticker", "expire", "option", "strike", "datatime", "trade", "size"]
stocks_columns = ["ticker", "datetime", "trade", "size"]


class IBKRTradesHistoryPage(WebSOCKPage, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        pass


class IBKRStockTradesHistoryPage(IBKRTradesHistoryPage):
    pass

class IBKROptionTradesHistoryPage(IBKRTradesHistoryPage):
    pass


class AlpacaTradesHistoryDownloader(Results, Logging, ABC):
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


class IBKRStockTradesHistoryDownloader(AlpacaTradesHistoryDownloader, page=IBKRStockTradesHistoryPage, columns=stocks_columns):
    def scope(self, products, **kwargs): return super().scope(products, instrument=Instrument.STOCK)


class IBKROptionTradesHistoryDownloader(AlpacaTradesHistoryDownloader, page=IBKROptionTradesHistoryPage, columns=options_columns):
    def scope(self, products, **kwargs): return super().scope(products, instrument=Instrument.OPTION)



