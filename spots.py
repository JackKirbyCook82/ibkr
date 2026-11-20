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
from finance.console import LoggingDecorators, LoggingSizing
from finance.variables import Collection, Variables
from finance.enumerations import Enumerations
from support.meta import NamespaceMeta
from support.pipeline import Pipelines

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrStockSpotsDownloader", "IbkrOptionSpotsDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrSpotsPage(IbkrPage, ABC, namespace={"instrument": None}, metaclass=NamespaceMeta):
    def __init__(self, *args, instrument, **kwargs):
        super().__init__(*args, **kwargs)
        self.__instrument = instrument

    def __call__(self, *args, products, **kwargs):
        securities = [product["security"] if "security" in product else self.source.security(product) for product in products]
        qualified = [security for security in securities if bool(security.conId)]
        unqualified = [security for security in securities if not bool(security.conId)]
        if unqualified: qualified.extend(self.source.qualify(unqualified))
        spots = self.execute(securities=qualified)
        return spots

    def execute(self, *args, **kwargs):
        spots = self.generator(*args, **kwargs)
        spots = pd.concat(list(spots), axis=0, ignore_index=True)
        return spots

    def generator(self, *args, securities, **kwargs):
        for security in securities:
            spot = self.spot(*args, security=security, instrument=self.instrument, **kwargs)
            yield spot

    @property
    def instrument(self): return self.__instrument


class IbkrStockSpotsPage(IbkrSpotsPage, instrument=Enumerations.Instrument.STOCK): pass
class IbkrOptionSpotsPage(IbkrSpotsPage, instrument=Enumerations.Instrument.OPTION): pass


class IbkrSpotsDownloader(IbkrStream):
    @Pipelines.Function(locator=0)
    @LoggingDecorators.Function(Collection[Variables.Ticker], Collection[Variables.Expire], sizing=LoggingSizing.OUTLET, title="Downloaded")
    def __call__(self, products, /, **kwargs):
        if not isinstance(products, list): products = [products]
        if not bool(products): return None
        spot = list(self.downloader(products, **kwargs))
        if not spot: return None
        bars = pd.concat(list(spot), axis=0, ignore_index=True)
        return bars

    def downloader(self, products, /, **kwargs):
        products = [products[index:index + self.limit] for index in range(0, len(products), self.limit)]
        for products in products:
            parameters = dict(products=products)
            bars = self.page(**parameters, **kwargs)
            if bars is None or bool(bars.empty): continue
            yield bars


class IbkrStockSpotsDownloader(IbkrSpotsDownloader, page=IbkrStockSpotsPage, instrument=Enumerations.Instrument.STOCK): pass
class IbkrOptionSpotsDownloader(IbkrSpotsDownloader, page=IbkrOptionSpotsPage, instrument=Enumerations.Instrument.OPTION): pass



