# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR Ticks Objects
@author: Jack Kirby Cook
@file:   ibkr/ticks.py

"""

from itertools import chain
from ib_async import Stock, util
from zoneinfo import ZoneInfo
from datetime import time as Time
from datetime import datetime as Datetime
from datetime import timezone as Timezone
from datetime import timedelta as Timedelta

from ibkr.website import IbkrPage
from finance.querys import Symbol
from support.custom import DateRange

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = []
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IkbrTicksHistoryPage(IbkrPage):
    def __call__(self, *args, product, price, frequency, history, **kwargs):
        assert frequency is not None and bool(frequency)
        assert history is not None and bool(history)
        if isinstance(product, Stock): security = product
        elif isinstance(product, Symbol):
            try: security = product["security"]
            except KeyError: security = self.security(product)
        else: raise TypeError(product)
        if not bool(security.conId): security = self.source.qualify(security)
        history = DateRange([Datetime.combine(date, Time.min, tzinfo=ZoneInfo("America/New_York")).astimezone(Timezone.utc) for date in history])
        parameters = dict(security=security, price=price, frequency=frequency, history=history)
        ticks = self.execute(*args, **parameters, **kwargs)
        return ticks

    def execute(self, *args, **kwargs):
        ticks = self.generator(*args, **kwargs)
        ticks = list(chain.from_iterable(ticks))
        ticks = util.df(ticks)
        ticks = self.parse(ticks)
        return ticks

    def ticks(self, *args, security, stop, **kwargs):
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



