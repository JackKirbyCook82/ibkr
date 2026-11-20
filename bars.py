# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR Bars Objects
@author: Jack Kirby Cook
@file:   ibkr/bars.py

"""

import pandas as pd
from abc import ABC
from zoneinfo import ZoneInfo
from datetime import time as Time
from datetime import timezone as Timezone
from datetime import datetime as Datetime

from ibkr.website import IbkrPage, IbkrStream
from ibkr.subscription import IbkrSubscription
from finance.console import LoggingDecorators, LoggingSizing
from finance.variables import Collection, Variables
from finance.enumerations import Enumerations
from finance.querys import Querys
from support.pipeline import Pipelines
from support.custom import DateRange

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrTradeStockBarsDownloader", "IbkrQuoteStockBarsDownloader", "IbkrTradeOptionBarsDownloader", "IbkrQuoteOptionBarsDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrBarsPage(IbkrPage, ABC):
    def __call__(self, *args, product, price, frequency, history, **kwargs):
        assert frequency is not None and bool(frequency)
        assert history is not None and bool(history)
        history = DateRange([Datetime.combine(date, Time.min, tzinfo=ZoneInfo("America/New_York")).astimezone(Timezone.utc) for date in history])
        duration = history.maximum - history.minimum
        try: security = product["security"]
        except KeyError: security = self.source.security(product)
        if not bool(security.conId): security = self.source.qualify(security)
        parameters = dict(security=security, price=price, frequency=frequency, history=history, duration=duration)
        bars = self.execute(*args, **parameters, **kwargs)
        return bars

    def execute(self, *args, **kwargs):
        bars = self.generator(*args, **kwargs)
        bars = pd.concat(list(bars), axis=0, ignore_index=True)
        return bars

    def generator(self, *args, security, history, **kwargs):
        symbol = Querys.Symbol(str(security.symbol).upper())
        with IbkrSubscription(self.source, product=symbol) as subscription:
            stop = history.stop
            bars = self.bars(*args, stop=stop, **kwargs)
            yield bars


class IbkrStockBarsPage(IbkrBarsPage): pass
class IbkrOptionBarsPage(IbkrBarsPage): pass


class IbkrBarsDownloader(IbkrStream):
    @Pipelines.Function(locator=0)
    @LoggingDecorators.Function(Collection[Variables.Ticker], Collection[Variables.Expire], sizing=LoggingSizing.OUTLET, title="Downloaded")
    def __call__(self, products, /, **kwargs):
        if not isinstance(products, list): products = [products]
        if not bool(products): return None
        bars = list(self.downloader(products, **kwargs))
        if not bars: return None
        bars = pd.concat(list(bars), axis=0)
        return bars

    def downloader(self, products, /, **kwargs):
        for product in products:
            parameters = dict(product=product, price=self.price)
            bars = self.page(**parameters, **kwargs)
            bars = bars.sort_values(by="datetime", ascending=False, inplace=False)
            bars = bars.reset_index(drop=True, inplace=False)
            if bars is None or bool(bars.empty): continue
            yield bars


class IbkrStockBarsDownloader(IbkrBarsDownloader, page=IbkrStockBarsPage, instrument=Enumerations.Instrument.STOCK): pass
class IbkrOptionBarsDownloader(IbkrBarsDownloader, page=IbkrOptionBarsPage, instrument=Enumerations.Instrument.OPTION): pass

class IbkrTradeStockBarsDownloader(IbkrStockBarsDownloader, price=Enumerations.Price.TRADE): pass
class IbkrQuoteStockBarsDownloader(IbkrStockBarsDownloader, price=Enumerations.Price.QUOTE): pass
class IbkrTradeOptionBarsDownloader(IbkrOptionBarsDownloader, price=Enumerations.Price.TRADE): pass
class IbkrQuoteOptionBarsDownloader(IbkrOptionBarsDownloader, price=Enumerations.Price.QUOTE): pass



