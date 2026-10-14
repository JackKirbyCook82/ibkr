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
__all__ = []
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IkbrBarsPage(IbkrPage, ABC):
    def __call__(self, *args, product, price, frequency, history, **kwargs):
        assert frequency is not None and bool(frequency)
        assert history is not None and bool(history)
        try: security = product["security"]
        except KeyError: security = self.security(product)
        if not bool(security.conId): security = self.qualify(security)
        history = DateRange([Datetime.combine(date, Time.min, tzinfo=ZoneInfo("America/New_York")).astimezone(Timezone.utc) for date in history])
        duration = history.maximum - history.minimum
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

    def bars(self, *args, security, stop, **kwargs):
        frequency = self.frequency(*args, **kwargs)
        duration = self.duration(*args, **kwargs)
        price = self.price(*args, **kwargs)
        parameters = dict(whatToShow=price, endDateTime=stop, durationStr=duration, barSizeSetting=frequency, useRTH=True)
        bars = self.source.connection.reqHistoricalData(security, **parameters)
        return bars

    def generator(self, *args, **kwargs):
        bars = self.bars(*args, **kwargs)
        yield bars


class IkbrBarsDownloader(IbkrDownloader):
    pass


class IkbrStockBarsDownloader(IbkrDownloader, instrument=Instrument.STOCK):
    pass


class IkbrOptionBarsDownloader(IbkrDownloader, instrument=Instrument.OPTION):
    pass



