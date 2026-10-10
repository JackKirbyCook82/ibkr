# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IKBR History Bars Objects
@author: Jack Kirby Cook
@file:   ibkr/history/bars.py

"""

from ib_async import Stock

from ibkr.website import IbkrPage, IkbrFormatters
from finance.querys import Symbol

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = []
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IkbrBarsHistoryPage(IbkrPage):
    def __call__(self, *args, product, price, frequency, history, **kwargs):
        assert frequency is not None and bool(frequency)
        assert history is not None and bool(history)
        if isinstance(product, Stock): security = product
        elif isinstance(product, Symbol):
            try: security = product["security"]
            except KeyError: security = self.security(product)
        else: raise TypeError(product)
        if not bool(security.conId): security = self.qualify(security)
        parameters = dict(security=security, price=price, frequency=frequency, history=history)
        contracts = self.execute(**parameters)
        return contracts

    def execute(self, *args, security, price, frequency, history, **kwargs):
        stop = IkbrFormatters.datetime(history.maximum)
        frequency = IkbrFormatters.frequency(frequency)
        duration = IkbrFormatters.duration(history)
        price = IkbrFormatters.price(price)
        parameters = dict(endDateTime=stop, durationStr=duration, barSizeSetting=frequency, whatToShow=price, useRTH=True)
        bars = self.source.connection.reqHistoricalData(security, **parameters)

