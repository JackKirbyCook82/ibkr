# -*- coding: utf-8 -*-
"""
Created on Fri Oct 16 2026
@name:   Ikbr Spot Objects
@author: Jack Kirby Cook
@file:   ikbr/spot.py

"""

import pandas as pd
from abc import ABC

from ibkr.website import IbkrPage, IbkrStream
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
        if unqualified: qualified.extend(self.source.qualify(unqualified))
        spot = self.execute(securities=qualified)
        return spot

    def execute(self, *args, **kwargs):
        spot = self.spot(*args, **kwargs)
        spot = pd.DataFrame.from_records(spot)
        spot = self.parse(spot, *args, **kwargs)
        return spot


class IbkrSpotDownloader(IbkrStream, page=IbkrSpotPage):
    def __call__(self, products, /, **kwargs):
        if not isinstance(products, list): products = [products]
        if not bool(products): return None
        spot = list(self.downloader(products, **kwargs))
        if not spot: return None
        bars = pd.concat(list(spot), axis=0)
        return bars

#        tickers = set(bars["tickers"].unique())
#        expires = set(bars["expires"].unique())
#        tickers = f"{','.join(tickers)}"
#        expires = f"{min(expires).strftime('%Y/%m/%d')}->{max(expires).strftime('%Y/%m/%d')}"
#        quantity = f"{len(bars):.0f}"
#        string = f"Downloaded[{tickers}, {expires}, {quantity}]"

    def downloader(self, products, /, **kwargs):
        products = [products[index:index + self.limit] for index in range(0, len(products), self.limit)]
        for products in products:
            parameters = dict(products=products)
            bars = self.page(**parameters, **kwargs)
            if bars is None or bool(bars.empty): continue
            yield bars


class IbkrStockSpotDownloader(IbkrSpotDownloader, instrument=Instrument.STOCK): pass
class IbkrOptionSpotDownloader(IbkrSpotDownloader, instrument=Instrument.OPTION): pass



