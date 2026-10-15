# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Website Objects
@author: Jack Kirby Cook
@file:   ibkr\website.py

"""

import ib_async
import numpy as np
import pandas as pd
import multiprocessing
from typing import Callable
from abc import ABC, ABCMeta
from dataclasses import dataclass
from datetime import datetime as DateTime
from functools import singledispatchmethod

from finance.querys import Symbol, Contract
from finance.enumerations import Frequency, Price, Right
from finance.reporting import Results
from finance.osi import OSI
from pyparsing import opAssoc
from webscraping.webpages import WebSOCKPage
from webscraping.websources import WebSOCKSource
from support.decorators import Dispatchers
from support.meta import CollectionMeta
from support.mixins import Logging

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrSocket", "IbkrPage", "IbkrDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrError(Exception): pass
class IbkrSubscriptionError(IbkrError): pass
class IbkrSubscriptionSecurityError(IbkrSubscriptionError): pass
class IbkrSubscriptionMarketError(IbkrSubscriptionError): pass
class IbkrSubscriptionLimitError(IbkrSubscriptionError): pass
class IbkrFrequencyError(IbkrError): pass
class IbkrFrequencyByError(IbkrFrequencyError): pass
class IbkrFrequencySpanError(IbkrFrequencyError): pass


@dataclass(frozen=True)
class IbkrColumn: name: str; code: str; parser: Callable
class IbkrColumns(metaclass=CollectionMeta):
    datetime = IbkrColumn("datetime", "time", lambda string: pd.to_datetime(string, utc=True))
    volume = IbkrColumn("volume", "volume", np.int64)
    size = IbkrColumn("size", "size", np.float32)
    supply = IbkrColumn("supply", "sizeAsk", np.float32)
    demand = IbkrColumn("demand", "sizeBid", np.float32)
    trade = IbkrColumn("trade", "price", np.float32)
    bid = IbkrColumn("bid", "priceBid", np.float32)
    ask = IbkrColumn("ask", "priceAsk", np.float32)
    open = IbkrColumn("open", "priceOpen", np.float32)
    close = IbkrColumn("close", "priceClose", np.float32)
    high = IbkrColumn("high", "priceHigh", np.float32)
    low = IbkrColumn("low", "priceLow", np.float32)


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


@dataclass(frozen=True)
class IbkrProduct:
    security: ib_async.Stock | ib_async.Option
    market: ib_async.Ticker


class IbkrSocketMeta(ABCMeta):
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        instance.connection = ib_async.IB()
        return instance


class IbkrSocket(WebSOCKSource, metaclass=IbkrSocketMeta):
    def __bool__(self): return super().__bool__() and self.connected
    def __len__(self): return len(self.registry)

    def __init__(self, *args, host, port, client, limit, **kwargs):
        assert isinstance(client, int) and isinstance(limit, int)
        super().__init__(*args, **kwargs)
        self.__registry = dict()
        self.__client = client
        self.__limit = limit
        self.__host = host
        self.__port = port

    def start(self): self.connection.connect(host=self.host, port=self.port, clientId=self.client)
    def stop(self): self.connection.disconnect()

    def subscribe(self, product):
        if len(self) >= self.limit: raise IbkrSubscriptionLimitError()
        with self.mutex:
            if "security" in product: security = product.security
            else: security = self.security(product)
            if not bool(security.conId): security = self.qualify(security)
            if security.conId in self.registry.keys(): return
            market = self.connection.reqMktData(security)
            product = IbkrProduct(security, market)
            self.registry[security.conId] = product

    def unsubscribe(self, product):
        assert isinstance(product, IbkrProduct)
        with self.mutex:
            try: product = self.registry[product.security.conId]
            except KeyError: return
            self.connection.cancelMktData(product.security)
            self.registry.pop(product.security.conId)

    @singledispatchmethod
    def qualify(self, security): raise TypeError(type(security))

    @qualify.register(list)
    def _(self, securities):
        qualified = self.connection.qualifyContracts(*securities)
        if len(securities) != len(qualified): raise IbkrSubscriptionSecurityError()
        if None in qualified: raise IbkrSubscriptionSecurityError()
        return qualified

    @qualify.register(ib_async.Stock)
    @qualify.register(ib_async.Option)
    def _(self, security):
        try: qualified = self.connection.qualifyContracts(security)[0]
        except IndexError: raise IbkrSubscriptionSecurityError()
        if qualified is None: raise IbkrSubscriptionSecurityError()
        return qualified

    @staticmethod
    def security(product):
        if product.record is Symbol: return ib_async.Stock(product.ticker, "SMART", "USD")
        elif product.record is Contract: return ib_async.Option(product.ticker, product.expire.strftime("%Y%m%d"), product.strike, str(product.right).upper()[0], "SMART")
        else: raise TypeError(type(product.record))

    @property
    def connected(self): return self.connection.isConnected()
    @property
    def registry(self): return self.__registry
    @property
    def client(self): return self.__client
    @property
    def limit(self): return self.__limit
    @property
    def host(self): return self.__host
    @property
    def port(self): return self.__port


class IbkrSubscriptionMeta(type):
    def __call__(cls, source, *args, products, **kwargs):
        assert isinstance(source, IbkrSocket) and isinstance(products, list)
        securities = source.qualify(products)
        for product, security in zip(products, securities): product["security"] = security
        for product in products: source.subscribe(product)
        instance = super().__call__(source, *args, products=products, **kwargs)
        return instance


# CREATE ANY IDENTITY FOR EACH SUBSCRIPTION CONTEXT
# STORE THE IBKR PRODUCT FOR EACH IDENTITY


class IbkrSubscription(object, metaclass=IbkrSubscriptionMeta):
    def __init__(self, source, *args, products, **kwargs):
        assert isinstance(source, IbkrSocket) and bool(source)
        self.__products = products
        self.__source = source

    def __enter__(self): return self
    def __exit__(self, error_type, error_value, error_traceback):
        for product in self.products:
            self.source.subscribe(product)

    @property
    def products(self): return self.__products
    @property
    def source(self): return self.__source


class IbkrPage(WebSOCKPage):
    @Dispatchers.Type(locator="security")
    def index(self, dataframe, *args, security, **kwargs): raise TypeError(type(security))

    @index.register(ib_async.Stock)
    def _(self, dataframe, *args, security, **kwargs):
        dataframe["ticker"] = str(security.symbol).upper()
        return dataframe

    @index.register(ib_async.Option)
    def _(self, dataframe, *args, security, **kwargs):
        dataframe["ticker"] = str(security.symbol).upper()
        dataframe["expire"] = DateTime.strptime("%Y%m%d", security.lastTradeDateOrContractMonth).date()
        dataframe["strike"] = float(security.strike)
        dataframe["right"] = {str(right).upper()[0]: right for right in Right}[security.right]
        dataframe["osi"] = DateTime[list(Contract)].apply(OSI)
        return dataframe

    @staticmethod
    def columns(dataframe, *args, **kwargs):
        columns = [column for column in list(dict(IbkrColumns).values()) if column.code in dataframe.columns]
        dataframe = dataframe[[column.code for column in columns]]
        dataframe = dataframe.rename(columns={column.code: column.name for column in columns}, inplace=False)
        for column in columns: dataframe[column.name] = dataframe[column.name].apply(column.parser)
        return dataframe

    @staticmethod
    def price(*args, price, **kwargs): return {Price.TRADE: "TRADES", Price.MID: "MIDPOINT", Price.BID: "BID", Price.ASK: "ASK", Price.QUOTE: "BID_ASK"}[price]
    @staticmethod
    def duration(*args, duration, **kwargs): return f"{int(duration.total_seconds())} S"
    @staticmethod
    def frequency(*args, frequency, **kwargs): return IbkrFrequencies(frequency)


class IbkrDownloader(Results, Logging, ABC):
    def __init_subclass__(cls, /, **kwargs):
        super().__init_subclass__(**kwargs)
        namespace = getattr(cls, "__namespace__", {})
        instrument = kwargs.get("instrument", namespace.get("instrument", None))
        page = kwargs.get("page", namespace.get("page", None))
        cls.__namespace__ = dict(instrument=instrument, page=page)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__page = self.namespace["page"](*args, **kwargs)
        self.__instrument = self.namespace["instrument"]

    def scope(self, products, **kwargs):
        if self.instrument is None: raise ValueError(self.instrument)
        return super().scope(products, instrument=self.instrument)

    @property
    def namespace(self): return type(self).__namespace__
    @property
    def instrument(self): return self.__instrument
    @property
    def page(self): return self.__page



