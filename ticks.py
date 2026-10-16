# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR Ticks Objects
@author: Jack Kirby Cook
@file:   ibkr/ticks.py

"""

import pandas as pd
from abc import ABC
from ib_async import util
from itertools import chain
from zoneinfo import ZoneInfo
from datetime import time as Time
from datetime import datetime as Datetime
from datetime import timezone as Timezone
from datetime import timedelta as Timedelta

from ibkr.website import IbkrPage, IbkrDownloader
from finance.enumerations import Instrument
from support.custom import DateRange

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrStockTicksDownloader", "IbkrOptionTicksDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrTicksPage(IbkrPage, ABC):
    def __call__(self, *args, product, price, frequency, history, **kwargs):
        assert frequency is not None and bool(frequency)
        assert history is not None and bool(history)
        history = DateRange([Datetime.combine(date, Time.min, tzinfo=ZoneInfo("America/New_York")).astimezone(Timezone.utc) for date in history])
        try: security = product["security"]
        except KeyError: security = self.source.security(product)
        if not bool(security.conId): security = self.source.qualify(security)
        parameters = dict(security=security, price=price, frequency=frequency, history=history)
        ticks = self.execute(*args, **parameters, **kwargs)
        return ticks

    def execute(self, *args, **kwargs):
        ticks = self.generator(*args, **kwargs)
        ticks = list(chain.from_iterable(ticks))
        ticks = util.df(ticks)
        ticks = self.columns(ticks, *args, **kwargs)
        ticks = self.index(ticks, *args, **kwargs)
        return ticks

    def generator(self, *args, history, **kwargs):
        stop = history.stop
        while stop > history.start:
            ticks = self.ticks(*args, stop=stop, **kwargs)
            if not ticks: break
            yield ticks
            stop = min(tick.time for tick in ticks)
            stop = stop - Timedelta(seconds=1)


class IbkrTicksDownloader(IbkrDownloader):
    def __call__(self, products, /, **kwargs):
        if not isinstance(products, list): products = [products]
        ticks = list(self.downloader(products, **kwargs))
        if not ticks: return None
        ticks = pd.concat(list(ticks), axis=0)
        return ticks

    def downloader(self, products, /, **kwargs):
        for product in products:
            scope = self.scope([products])
            ticks = self.page(product=product, **kwargs)
            ticks = ticks.sort_values(by="datetime", ascending=False, inplace=False)
            if ticks is None or bool(ticks.empty): continue
            results = self.results(scope=scope, size=len(ticks))
            self.console("Downloaded", results)
            yield ticks


class IbkrStockTicksDownloader(IbkrDownloader, instrument=Instrument.STOCK): pass
class IbkrOptionTicksDownloader(IbkrDownloader, instrument=Instrument.OPTION): pass



