# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR Ticks Objects
@author: Jack Kirby Cook
@file:   ibkr/ticks.py

"""

import pandas as pd
from abc import ABC
from zoneinfo import ZoneInfo
from datetime import time as Time
from datetime import datetime as Datetime
from datetime import timezone as Timezone
from datetime import timedelta as Timedelta

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
__all__ = ["IbkrTradeStockTicksDownloader", "IbkrQuoteStockTicksDownloader", "IbkrTradeOptionTicksDownloader", "IbkrQuoteOptionTicksDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrTicksPage(IbkrPage, ABC):
    def __call__(self, *args, product, price, frequency, history, sparse=False, **kwargs):
        assert frequency is not None and bool(frequency)
        assert history is not None and bool(history)
        history = DateRange([Datetime.combine(date, Time.min, tzinfo=ZoneInfo("America/New_York")).astimezone(Timezone.utc) for date in history])
        try: security = product["security"]
        except KeyError: security = self.source.security(product)
        if not bool(security.conId): security = self.source.qualify(security)
        parameters = dict(security=security, price=price, frequency=frequency, history=history, sparse=sparse)
        ticks = self.execute(*args, **parameters, **kwargs)
        return ticks

    def execute(self, *args, **kwargs):
        ticks = self.generator(*args, **kwargs)
        ticks = pd.concat(list(ticks), axis=0, ignore_index=True)
        return ticks

    def generator(self, *args, security, history, **kwargs):
        symbol = Querys.Symbol(str(security.symbol).upper())
        with IbkrSubscription(self.source, product=symbol) as subscription:
            stop = history.stop
            while stop > history.start:
                ticks = self.ticks(*args, stop=stop, **kwargs)
                if not ticks: break
                yield ticks
                stop = min(tick.time for tick in ticks)
                stop = stop - Timedelta(seconds=1)


class IbkrStockTicksPage(IbkrTicksPage): pass
class IbkrOptionTicksPage(IbkrTicksPage): pass


class IbkrTicksDownloader(IbkrStream):
    @Pipelines.Function(locator=0)
    @LoggingDecorators.Function(Collection[Variables.Ticker], Collection[Variables.Expire], sizing=LoggingSizing.OUTLET, title="Downloaded")
    def __call__(self, products, /, **kwargs):
        if not isinstance(products, list): products = [products]
        if not bool(products): return None
        ticks = list(self.downloader(products, **kwargs))
        if not ticks: return None
        ticks = pd.concat(list(ticks), axis=0)
        return ticks

    def downloader(self, products, /, **kwargs):
        for product in products:
            parameters = dict(product=product, price=self.price)
            ticks = self.page(**parameters, **kwargs)
            ticks = ticks.sort_values(by="datetime", ascending=False, inplace=False)
            ticks = ticks.reset_index(drop=True, inplace=False)
            if ticks is None or bool(ticks.empty): continue
            yield ticks


class IbkrStockTicksDownloader(IbkrTicksDownloader, page=IbkrStockTicksPage, instrument=Enumerations.Instrument.STOCK): pass
class IbkrOptionTicksDownloader(IbkrTicksDownloader, page=IbkrOptionTicksPage, instrument=Enumerations.Instrument.OPTION): pass

class IbkrTradeStockTicksDownloader(IbkrStockTicksDownloader, price=Enumerations.Price.TRADE): pass
class IbkrQuoteStockTicksDownloader(IbkrStockTicksDownloader, price=Enumerations.Price.QUOTE): pass
class IbkrTradeOptionTicksDownloader(IbkrOptionTicksDownloader, price=Enumerations.Price.TRADE): pass
class IbkrQuoteOptionTicksDownloader(IbkrOptionTicksDownloader, price=Enumerations.Price.QUOTE): pass



