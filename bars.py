# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR Bars Objects
@author: Jack Kirby Cook
@file:   ibkr/bars.py

"""

from abc import ABC
from ib_async import util
from itertools import chain
from zoneinfo import ZoneInfo
from datetime import time as Time
from datetime import timezone as Timezone
from datetime import datetime as Datetime

from ibkr.website import IbkrPage, IbkrDownloader
from finance.enumerations import Instrument
from support.custom import DateRange

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IkbrStockBarsDownloader", "IkbrOptionBarsDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IkbrBarsPage(IbkrPage, ABC):
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
        bars = list(chain.from_iterable(bars))
        bars = util.df(bars)
        bars = self.columns(bars, *args, **kwargs)
        bars = self.index(bars, *args, **kwargs)
        return bars

    def generator(self, *args, history, **kwargs):
        stop = history.stop
        bars = self.bars(*args, stop=stop, **kwargs)
        yield bars


class IkbrBarsDownloader(IbkrDownloader):
    pass


class IkbrStockBarsDownloader(IbkrDownloader, instrument=Instrument.STOCK):
    pass


class IkbrOptionBarsDownloader(IbkrDownloader, instrument=Instrument.OPTION):
    pass



