# -*- coding: utf-8 -*-
"""
Created on Fri Oct 16 2026
@name:   Ikbr Spot Objects
@author: Jack Kirby Cook
@file:   ikbr/spot.py

"""

import pandas as pd
from abc import ABC

from ibkr.website import IbkrPage, IbkrDownloader
from finance.enumerations import Instrument

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrStockSpotDownloader", "IbkrOptionSpotDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrSpotPage(IbkrPage, ABC):
    def __call__(self, *args, products, **kwargs):
        securities = [product["security"] if "security" in product else self.source.security(product) for product in products]
        qualified = [security for security in securities if bool(security.conId)]
        unqualified = [security for security in securities if not bool(security.conId)]
        securities = qualified + self.source.qualify(unqualified)
        spot = self.execute(securities=securities)
        return spot

    def execute(self, *args, **kwargs):
        spot = self.spot(*args, **kwargs)
        spot = pd.DataFrame.from_records(spot)
        spot = self.columns(spot, *args, **kwargs)
        spot = self.index(spot, *args, **kwargs)
        return spot


class IbkrSpotDownloader(IbkrDownloader, page=IbkrSpotPage):
    def __call__(self, products, /, **kwargs):
        if not isinstance(products, list): products = [products]
        spot = list(self.downloader(products, **kwargs))
        if not spot: return None
        bars = pd.concat(list(spot), axis=0)
        return bars

    def downloader(self, products, /, **kwargs):
        products = [products[index:index + self.limit] for index in range(0, len(products), self.limit)]
        for products in products:
            scope = self.scope(products)
            parameters = dict(products=products)
            bars = self.page(**parameters, **kwargs)
            if bars is None or bool(bars.empty): continue
            results = self.results(scope=scope, size=len(bars))
            self.console("Downloaded", results)
            yield bars


class IbkrStockSpotDownloader(IbkrSpotDownloader, instrument=Instrument.STOCK): pass
class IbkrOptionSpotDownloader(IbkrSpotDownloader, instrument=Instrument.OPTION): pass



