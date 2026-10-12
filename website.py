# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Website Objects
@author: Jack Kirby Cook
@file:   ibkr\website.py

"""

from abc import ABC
from dataclasses import dataclass
from ib_async import IB, Stock, Option
from functools import singledispatchmethod

from finance.querys import Symbol, Contract
from finance.enumerations import Frequency, Price
from finance.reporting import Results
from webscraping.webpages import WebSOCKPage
from webscraping.websources import WebSOCKSource
from support.meta import CollectionMeta
from support.mixins import Logging

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrSocket", "IbkrPage", "IbkrDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrError(Exception): pass
class IbkrSecurityError(IbkrError): pass
class IbkrFrequencyError(IbkrError): pass
class IbkrFrequencyByError(IbkrFrequencyError): pass
class IbkrFrequencySpanError(IbkrFrequencyError): pass


@dataclass(frozen=True)
class IbkrFrequency: by: Frequency; code: str; span: list[int]
class IbkrFrequencies(metaclass=CollectionMeta):
    minutes = IbkrFrequency(Frequency.MINUTELY, "min", [1, 2, 3, 5, 10, 15, 20, 30])
    hours = IbkrFrequency(Frequency.HOURLY, "hour", [1, 2, 3, 4, 8])
    months = IbkrFrequency(Frequency.MONTHLY, "month", [1])
    weeks = IbkrFrequency(Frequency.WEEKLY, "week", [1])
    days = IbkrFrequency(Frequency.DAILY, "day", [1])

    def __new__(cls, frequency):
        by, span = frequency.by, frequency.span
        frequencies = {frequency.by: frequency for frequency in dict(cls).values()}
        if by not in frequencies.keys(): raise IbkrFrequencyByError()
        if span not in frequencies[by].span: raise IbkrFrequencySpanError()
        return f"{int(span)} {str(frequencies[by].code)}{'s' if span > 1 else ''}"


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

    @singledispatchmethod
    def qualify(self, security): raise TypeError(type(security))

    @qualify.register(list)
    def _(self, securities): return self.connection.qualifyContracts(*securities)

    @qualify.register(Stock)
    @qualify.register(Option)
    def _(self, security):
        try: return self.connection.qualifyContracts(security)[0]
        except IndexError: raise IbkrSecurityError()

    @property
    def connected(self): return self.connection.isConnected()
    @property
    def client(self): return self.__client
    @property
    def host(self): return self.__host
    @property
    def port(self): return self.__port


class IbkrPage(WebSOCKPage):
    @staticmethod
    def price(*args, price, **kwargs): return {Price.TRADE: "TRADES", Price.MID: "MIDPOINT", Price.BID: "BID", Price.ASK: "ASK", Price.QUOTE: "BID_ASK"}[price]
    @staticmethod
    def duration(*args, duration, **kwargs): return f"{int(duration.total_seconds())} S"
    @staticmethod
    def frequency(*args, frequency, **kwargs): return IbkrFrequencies(frequency)

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




