# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR Ticks Objects
@author: Jack Kirby Cook
@file:   ibkr/ticks.py

"""

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
__all__ = []
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IkbrTicksPage(IbkrPage, ABC):
    def __call__(self, *args, products, price, frequency, history, **kwargs):
        assert frequency is not None and bool(frequency)
        assert history is not None and bool(history)
        history = DateRange([Datetime.combine(date, Time.min, tzinfo=ZoneInfo("America/New_York")).astimezone(Timezone.utc) for date in history])
        parameters = dict(price=price, frequency=frequency, history=history)
        with self.source.subscription(products) as subscription:
            bars = self.execute(subscription, *args, **parameters, **kwargs)
        return bars

#        try: security = product["security"]
#        except KeyError: security = self.security(product)
#        if not bool(security.conId): security = self.qualify(security)
#        ticks = self.execute(*args, **parameters, **kwargs)
#        return ticks

    def execute(self, subscription, *args, **kwargs):
        ticks = self.generator(subscription, *args, **kwargs)
        ticks = list(chain.from_iterable(ticks))
        ticks = util.df(ticks)
        ticks = self.columns(ticks, *args, **kwargs)
        ticks = self.index(ticks, *args, **kwargs)
        return ticks

    def ticks(self, subscription, *args, security, stop, **kwargs):
        price = self.price(*args, **kwargs)
        parameters = dict(whatToShow=price, startDateTime="", endDateTime=stop, numberOfTicks=1000, useRTH=True, ignoreSize=False)
        ticks = self.source.connection.reqHistoricalTicks(security, **parameters)
        return ticks

    def generator(self, *args, history, **kwargs):
        stop = history.stop
        while stop > history.start:
            ticks = self.ticks(*args, stop=stop, **kwargs)
            if not ticks: break
            yield ticks
            stop = min(tick.time for tick in ticks)
            stop = stop - Timedelta(seconds=1)


class IkbrTicksDownloader(IbkrDownloader):
    pass


class IkbrStockTicksDownloader(IbkrDownloader, instrument=Instrument.STOCK):
    pass


class IkbrOptionTicksDownloader(IbkrDownloader, instrument=Instrument.OPTION):
    pass



