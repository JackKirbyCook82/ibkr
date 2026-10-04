# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR Latest Trades Objects
@author: Jack Kirby Cook
@file:   ikbr/latest/trades.py

"""

from abc import ABC

from finance.enumerations import Instrument
from finance.reporting import Results
from webscraping.webpages import WebSOCKPage
from support.mixins import Logging

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IKBRStockTradesLatestDownloader", "IKBROptionTradesLatestDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


options_columns = ["ticker", "expire", "option", "strike", "datatime", "trade", "size"]
stocks_columns = ["ticker", "datetime", "trade", "size"]


class IKBRTradesLatestPage(WebSOCKPage, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        pass


class IKBRStockTradesLatestPage(IKBRTradesLatestPage):
    pass

class IKBROptionTradesLatestPage(IKBRTradesLatestPage):
    pass


class IKBRTradesLatestDownloader(Results, Logging, ABC):
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


class IKBRStockTradesLatestDownloader(IKBRTradesLatestDownloader, page=IKBRStockTradesLatestPage, stocks=stocks_columns):
    def scope(self, products, **kwargs): return super().scope(products, instrument=Instrument.STOCK)


class IKBROptionTradesLatestDownloader(IKBRTradesLatestDownloader, page=IKBROptionTradesLatestPage, columns=options_columns):
    def scope(self, products, **kwargs): return super().scope(products, instrument=Instrument.OPTION)




