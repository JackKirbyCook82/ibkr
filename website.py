# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Website Objects
@author: Jack Kirby Cook
@file:   ibkr\website.py

"""

from abc import ABC
from typing import Callable
from dataclasses import dataclass
from datetime import date as Date
from ib_async import IB, Stock, Option
from functools import singledispatchmethod

from finance.querys import Symbol, Contract
from finance.enumerations import Frequency, Price
from finance.reporting import Results
from webscraping.webpages import WebSOCKPage
from webscraping.websources import WebSOCKSource
from support.custom import DateRange
from support.mixins import Logging

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrSocket", "IbkrPage", "IbkrDownloader", "IkbrFormatters"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IkbrError(Exception): pass
class IkbrPriceError(IkbrError): pass
class IkbrSecurityError(IkbrError): pass
class IkbrFrequencyError(IkbrError): pass
class IkbrFrequencyByError(IkbrFrequencyError): pass
class IkbrFrequencySpanError(IkbrFrequencyError): pass


@dataclass(frozen=True)
class IbkrFrequency: by: Frequency; code: str; span: list[int]

@dataclass(frozen=True)
class IbkrParser: name: str; parser: Callable


class IkbrFrequencies:
    minutes = IbkrFrequency(Frequency.MINUTELY, "min", [1, 2, 3, 5, 10, 15, 20, 30])
    hours = IbkrFrequency(Frequency.HOURLY, "hour", [1, 2, 3, 4, 8])
    months = IbkrFrequency(Frequency.MONTHLY, "month", [1])
    weeks = IbkrFrequency(Frequency.WEEKLY, "week", [1])
    days = IbkrFrequency(Frequency.DAILY, "day", [1])

    def __new__(cls, frequency):
        by, span = frequency.by, frequency.span
        frequencies = [cls.months, cls.weeks, cls.days, cls.hours, cls.minutes]
        frequencies = {frequency.by: frequency for frequency in frequencies}
        if by not in frequencies.keys(): raise IkbrFrequencyByError()
        if span not in frequencies[by].span: raise IkbrFrequencySpanError()
        return f"{int(span)} {str(frequencies[by].code)}{'s' if span > 1 else ''}"


class IkbrFormatters:
    @staticmethod
    def frequency(frequency): return IkbrFrequencies(frequency)

    @staticmethod
    def duration(daterange):
        assert isinstance(daterange, DateRange)
        seconds = int((daterange.maximum - daterange.minimum).total_seconds())
        return f"{seconds} S"

    @staticmethod
    def datetime(date):
        assert isinstance(date, Date)
        string = date.strftime("%Y%m%d %H:%M:%S")
        return f"{string} US/Eastern"

    @staticmethod
    def price(price):
        assert isinstance(price, (set, Price))
        prices = {Price.TRADE: "TRADES", Price.MID: "MIDPOINT", Price.BID: "BID", Price.ASK: "ASK", {Price.BID, Price.ASK}: "BID_ASK"}
        if price not in prices.keys: raise IkbrPriceError()
        return prices[price]


class IbkrSocket(WebSOCKSource):
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        instance.connection = IB()
        return instance

    def __bool__(self): return super().__bool__() and self.connected
    def __init__(self, *args, host, port, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__client = client
        self.__host = host
        self.__port = port

    def start(self): self.connection.connect(host=self.host, port=self.port, clientId=self.client)
    def stop(self): self.connection.disconnect()
    def subscribe(self, security): self.connection.reqMktData(security)
    def unsubscribe(self, security): self.connection.cancelMktData(security)

    @property
    def connected(self): return self.connection.isConnected()
    @property
    def client(self): return self.__client
    @property
    def host(self): return self.__host
    @property
    def port(self): return self.__port


class IbkrPage(WebSOCKPage):
    @singledispatchmethod
    def qualify(self, security): raise TypeError(type(security))

    @qualify.register(list)
    def _(self, securities): return self.source.connection.qualifyContracts(*securities)

    @qualify.register(Stock)
    @qualify.register(Option)
    def _(self, security):
        try: return self.source.connection.qualifyContracts(security)[0]
        except IndexError: raise IkbrSecurityError()

    @singledispatchmethod
    @staticmethod
    def security(content): raise TypeError(type(content))

    @security.register(Contract)
    @staticmethod
    def _(contract): return Option(contract.ticker, contract.expire.strftime("%Y%m%d"), contract.strike, str(contract.option).upper()[0], "SMART")

    @security.register(Symbol)
    @staticmethod
    def _(symbol): return Stock(symbol.ticker, "SMART", "USD")


class IbkrDownloader(Results, Logging, ABC):
    pass




