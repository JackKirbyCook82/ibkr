# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Website Objects
@author: Jack Kirby Cook
@file:   ibkr\website.py

"""

from abc import ABC
from dataclasses import dataclass
from functools import singledispatchmethod
from ib_async import IB, Stock, Option

from finance.querys import Symbol, Contract
from finance.enumerations import Frequency
from finance.reporting import Results
from webscraping.webpages import WebSOCKPage
from webscraping.websources import WebSOCKSource
from support.mixins import Logging

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrSocket", "IbkrPage", "IbkrDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IkbrError(Exception): pass
class IkbrSecurityError(IkbrError): pass
class IkbrFrequencyError(IkbrError): pass
class IkbrFrequencyByError(IkbrFrequencyError): pass
class IkbrFrequencySpanError(IkbrFrequencyError): pass


@dataclass(frozen=False)
class IbkrFrequency:
    by: Frequency; code: str; span: list[int]

    def __call__(self, span):
        if span not in self.span: raise IkbrFrequencySpanError()
        return f"{int(span)} {str(self.code)}{'s' if span > 1 else ''}"


frequency_minutes = IbkrFrequency(Frequency.MINUTELY, "min", [1, 2, 3, 5, 10, 15, 20, 30])
frequency_hours = IbkrFrequency(Frequency.HOURLY, "hour", [1, 2, 3, 4, 8])
frequency_months = IbkrFrequency(Frequency.MONTHLY, "month", [1])
frequency_weeks = IbkrFrequency(Frequency.WEEKLY, "week", [1])
frequency_days = IbkrFrequency(Frequency.DAILY, "day", [1])
frequencies = [frequency_months, frequency_weeks, frequency_days, frequency_hours, frequency_minutes]
frequencies = {frequency.by: frequency for frequency in frequencies}


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

    @staticmethod
    def frequency(*args, frequency, **kwargs):
        if frequency.by not in frequencies.keys(): raise IkbrFrequencyByError()
        return frequencies[frequency.by](frequency.span)


class IbkrDownloader(Results, Logging, ABC):
    pass




