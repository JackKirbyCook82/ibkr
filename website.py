# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Website Objects
@author: Jack Kirby Cook
@file:   ibkr\website.py

"""

import time
import ib_async
import itertools
import numpy as np
import pandas as pd
from typing import Callable
from abc import ABC, ABCMeta
from dataclasses import dataclass
from datetime import datetime as Datetime
from functools import singledispatchmethod

from finance.querys import Symbol, Contract
from finance.enumerations import Frequency, Price, Right, Instrument
from finance.reporting import Results
from finance.osi import OSI
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
class IbkrFrequencyError(IbkrError): pass
class IbkrFrequencyByError(IbkrFrequencyError): pass
class IbkrFrequencySpanError(IbkrFrequencyError): pass
class IbkrSocketError(IbkrError): pass
class IbkrSocketSecurityError(IbkrError): pass
class IbkrSocketMarketError(IbkrSocketError): pass
class IbkrSocketIdentityError(IbkrSocketError): pass
class IbkrSocketLimitError(IbkrSocketError): pass


@dataclass(frozen=True)
class IbkrColumn: name: str; code: str; parser: Callable
class IbkrColumns(metaclass=CollectionMeta):
    datetime = IbkrColumn("datetime", "time", lambda string: pd.to_datetime(string, utc=True))
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


@dataclass(frozen=True, slots=True)
class IbkrIdentity: host: str; port: int; client: int

@dataclass(frozen=False, slots=False)
class IbkrStructure:
    security: ib_async.Stock | ib_async.Option
    market: ib_async.Ticker
    references: int = 1


class IbkrSocketMeta(ABCMeta):
    instance = None

    def __call__(cls, *args, host, port, client=1, **kwargs):
        identity = IbkrIdentity(host, port, client)
        if type(cls).instance is not None:
            if cls.instance.identity != identity: raise IbkrSocketIdentityError()
            else: return type(cls).instance
        instance = super().__call__(*args, identity=identity, **kwargs)
        instance.connection = ib_async.IB()
        type(cls).instance = instance
        return instance


class IbkrSocket(WebSOCKSource, metaclass=IbkrSocketMeta):
    def __bool__(self): return super().__bool__() and self.connected
    def __init__(self, *args, identity, limit=80, **kwargs):
        super().__init__(*args, **kwargs)
        self.__structures = dict()
        self.__securities = dict()
        self.__initialized = set()
        self.__limit = int(limit)
        self.__identity = identity

    def start(self): self.connection.connect(host=self.host, port=self.port, clientId=self.client)
    def stop(self): self.connection.disconnect()

    def prepare(self, product, timeout=2):
        if product in self.initialized: return
        stop = time.monotonic() + timeout
        while not self.ready(product):
            remaining = stop - time.monotonic()
            if remaining <= 0: raise IbkrSocketMarketError(product)
            self.connection.waitOnUpdate(timeout=remaining)
        self.initialized.add(product)

    def ready(self, product):
        market = self.structures[product].market
        return not np.isnan(market.bid) and not np.isnan(market.ask)

    def subscribe(self, product):
        with self.mutex:
            try: self.structures[product].references += 1
            except KeyError:
                if self.capacity <= 0: raise IbkrSocketLimitError()
                self.structures[product] = self.create(product)

    def unsubscribe(self, product):
        with self.mutex:
            try: structure = self.structures[product]
            except KeyError: return
            structure.references -= 1
            if structure.references == 0:
                self.destroy(product)
                del self.structures[product]

    def create(self, product):
        try: security = self.securities[product]
        except KeyError: security = self.security(product)
        if not bool(security.conId): security = self.qualify(security)
        market = self.connection.reqMktData(security)
        self.securities[product] = security
        return IbkrStructure(security, market)

    def destroy(self, product):
        structure = self.structures[product]
        assert structure.references == 0
        security = structure.security
        self.connection.cancelMktData(security)
        self.initialized.discard(product)

    def security(self, product):
        try: return self.securities[product]
        except KeyError: pass
        if product.record is Symbol: return ib_async.Stock(product.ticker, "SMART", "USD")
        elif product.record is Contract: return ib_async.Option(product.ticker, product.expire.strftime("%Y%m%d"), product.strike, str(product.right).upper()[0], "SMART")
        else: raise TypeError(type(product.record))

    @singledispatchmethod
    def qualify(self, security): raise TypeError(type(security))

    @qualify.register(list)
    def _(self, securities):
        qualified = self.connection.qualifyContracts(*securities)
        if len(securities) != len(qualified): raise IbkrSocketSecurityError()
        if None in qualified: raise IbkrSocketSecurityError()
        return qualified

    @qualify.register(ib_async.Stock)
    @qualify.register(ib_async.Option)
    def _(self, security):
        try: qualified = self.connection.qualifyContracts(security)[0]
        except IndexError: raise IbkrSocketSecurityError()
        if qualified is None: raise IbkrSocketSecurityError()
        return qualified

    @property
    def capacity(self): return self.limit - self.usage
    @property
    def usage(self): return len(self.securities)

    @property
    def connected(self): return self.connection.isConnected()
    @property
    def client(self): return self.identity.client
    @property
    def host(self): return self.identity.host
    @property
    def port(self): return self.identity.port

    @property
    def structures(self): return self.__structures
    @property
    def securities(self): return self.__securities
    @property
    def initialized(self): return self.__initialized
    @property
    def identity(self): return self.__identity
    @property
    def limit(self): return self.__limit


@dataclass(frozen=True, slots=True)
class IbkrVolatility: historic: float; realized: float; predicted: float

@dataclass(frozen=True, slots=True)
class IbkrDividends: historic: float; predicted: float

@dataclass(frozen=True, slots=True)
class IbkrPrice: trade: float; bid: float; ask: float

@dataclass(frozen=True, slots=True)
class IbkrSize: size: int; demand: int; supply: int

@dataclass(frozen=True, slots=True)
class IbkrSnapshot: datetime: Datetime; instrument: Instrument; product: object; price: IbkrPrice; size: IbkrSize; volume: int

@dataclass(frozen=True, slots=True)
class IbkrStockSnapshot(IbkrSnapshot): volatility: IbkrVolatility; dividends: IbkrDividends

@dataclass(frozen=True, slots=True)
class IbkrOptionSnapshot(IbkrSnapshot): interest: int


class IbkrSubscriptionMeta(type):
    def __call__(cls, source, *args, **kwargs):
        assert isinstance(source, IbkrSocket)
        products = list()
        try:
            for product in kwargs.get("products", []):
                source.subscribe(product)
                products.append(product)
        except Exception:
            for product in products:
                source.unsubscribe(product)
            raise
        instance = super().__call__(source, *args, products=products, **kwargs)
        return instance


class IbkrSubscription(object, metaclass=IbkrSubscriptionMeta):
    def __init__(self, source, *args, products, **kwargs):
        assert isinstance(products, list) and bool(products)
        assert isinstance(source, IbkrSocket)
        self.__products = products
        self.__source = source

    def __enter__(self): return self
    def __exit__(self, error_type, error_value, error_traceback):
        for product in self.products:
            self.source.unsubscribe(product)

    def __iter__(self):
        for product in self.products:
            yield self.snapshot(product)

    def __getitem__(self, product):
        return self.snapshot(product)

    def snapshot(self, product):
        self.source.prepare(product)
        security = self.source.structures[product].security
        market = self.source.structures[product].market
        size = IbkrSize(market.lastSize, market.bidSize, market.askSize)
        price = IbkrPrice(market.last, market.bid, market.ask)
        parameters = dict(datetime=market.time, price=price, size=size)
        product = dict(product.items())
        if isinstance(security, ib_async.Stock):
            volatility = IbkrVolatility(market.histVolatility, market.rtHistVolatility, market.impliedVolatility)
            dividends = IbkrDividends(market.dividends.past12Months, market.dividends.next12Months)
            snapshot = IbkrStockSnapshot(instrument=Instrument.STOCK, volatility=volatility, dividends=dividends, volume=market.volume, **parameters, **product)
        elif isinstance(security, ib_async.Option):
            volume = {Right.CALL: market.callVolume, Right.PUT: market.putVolume}[product["right"]]
            interest = {Right.CALL: market.callOpenInterest, Right.PUT: market.putOpenInterest}[product["right"]]
            snapshot = IbkrOptionSnapshot(instrument=Instrument.OPTION, volume=volume, interest=interest, **parameters, **product)
        else: raise TypeError(type(security))
        return snapshot

    @property
    def products(self): return self.__products
    @property
    def source(self): return self.__source


class IbkrPage(WebSOCKPage):
    def chain(self, *args, security, **kwargs):
        parameters = dict(underlyingSymbol=security.symbol, futFopExchange="", underlyingSecType="STK", underlyingConId=security.conId)
        chain = self.source.connection.reqSecDefOptParams(**parameters)
        expires = [Datetime.strptime(expire, "%Y%m%d").date() for expire in chain.expirations]
        expires = [expire for expire in expires if expire in kwargs.get("expires", expires)]
        strikes = list(map(float, chain.strikes))
        strikes = [strike for strike in list(map(float, chain.strikes)) if strike in kwargs.get("strikes", strikes)]
        rights = [str(right).upper()[0] for right in list(Right)]
        parameters = dict(symbol=security.symbol, exchange=chain.exchange, currency="USD", multiplier=chain.multiplier, tradingClass=chain.tradingClass)
        generator = itertools.product(expires, strikes, rights)
        function = lambda expire, strike, right: ib_async.Option(**parameters, lastTradeDateOrContractMonth=expire, strike=strike, right=right)
        chain = [function(expire, strike, right) for expire, strike, right in generator]
        chain = self.source.qualify(chain)
        return chain

    def bars(self, *args, security, stop, **kwargs):
        frequency = self.frequency(*args, **kwargs)
        duration = self.duration(*args, **kwargs)
        price = self.price(*args, **kwargs)
        parameters = dict(whatToShow=price, endDateTime=stop, durationStr=duration, barSizeSetting=frequency, useRTH=True)
        bars = self.source.connection.reqHistoricalData(security, **parameters)
        return bars

    def ticks(self, *args, security, stop, **kwargs):
        price = self.price(*args, **kwargs)
        parameters = dict(whatToShow=price, startDateTime="", endDateTime=stop, numberOfTicks=1000, useRTH=True, ignoreSize=False)
        ticks = self.source.connection.reqHistoricalTicks(security, **parameters)
        return ticks

    def spot(self, *args, securities, **kwargs):
        product = lambda content: {"product": content.contract.symbol, "time": content.time}
        trade = lambda content: {"price": content.last, "size": content.lastSize}
        quote = lambda content: {"priceBid": content.bid, "priceAsk": content.ask, "sizeBid": content.bidSize, "sizeAsk": content.askSize}
        data = self.source.connection.reqTickers(*securities)
        spot = [product(content) | trade(content) | quote(content) for content in data]
        return spot

    @Dispatchers.Type(locator="security")
    def index(self, dataframe, *args, security, **kwargs): raise TypeError(type(security))

    @index.register(ib_async.Stock)
    def _(self, dataframe, *args, security, **kwargs):
        dataframe["ticker"] = str(security.symbol).upper()
        return dataframe

    @index.register(ib_async.Option)
    def _(self, dataframe, *args, security, **kwargs):
        dataframe["ticker"] = str(security.symbol).upper()
        dataframe["expire"] = Datetime.strptime(security.lastTradeDateOrContractMonth, "%Y%m%d").date()
        dataframe["strike"] = float(security.strike)
        dataframe["right"] = {str(right).upper()[0]: right for right in Right}[security.right]
        dataframe["osi"] = dataframe[list(Contract)].apply(OSI)
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
        price = kwargs.get("price", namespace.get("price", None))
        limit = kwargs.get("limit", namespace.get("limit", 80))
        page = kwargs.get("page", namespace.get("page", None))
        namespace = dict(instrument=instrument, limit=limit, price=price, page=page)
        cls.__namespace__ = namespace

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__page = self.namespace["page"](*args, **kwargs)
        self.__instrument = self.namespace["instrument"]
        self.__price = self.namespace["price"]
        self.__limit = self.namespace["limit"]

    def scope(self, products, **kwargs):
        if self.instrument is None: raise ValueError(self.instrument)
        return super().scope(products, instrument=self.instrument)

    @property
    def namespace(self): return type(self).__namespace__
    @property
    def instrument(self): return self.__instrument
    @property
    def price(self): return self.__price
    @property
    def limit(self): return self.__limit
    @property
    def page(self): return self.__page



