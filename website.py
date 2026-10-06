# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Website Objects
@author: Jack Kirby Cook
@file:   ibkr\website.py

"""

from abc import ABC
from functools import singledispatchmethod
from ib_async import IB, Stock, Option

from finance.querys import Symbol, Contract
from finance.reporting import Results
from webscraping.webpages import WebSOCKPage
from webscraping.websources import WebSOCKSource
from support.mixins import Logging

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = []
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


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

    def qualify(self, securities): self.connection.qualifyContracts(*securities)
    def subscribe(self, security): self.connection.reqMktData(security)
    def unsubscribe(self, security): self.connection.cancelMktData(security)

    def start(self): return self.connection.connect(host=self.host, port=self.port, clientId=self.client)
    def stop(self): return self.connection.disconnect()

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
    @staticmethod
    def security(product): raise TypeError(type(product))

    @security.register(Contract)
    @staticmethod
    def contract(contract): return Option(contract.ticker, contract.expire.strftime("%Y%m%d"), contract.strike, str(contract.option).upper()[0], "SMART")

    @security.register(Symbol)
    @staticmethod
    def symbol(symbol): return Stock(symbol.ticker, "SMART", "USD")


class IbkrDownloader(Results, Logging, ABC):
    pass




