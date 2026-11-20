# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Subscription Objects
@author: Jack Kirby Cook
@file:   ibkr\subscription.py

"""

import ib_async
import pandas as pd
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime as Datetime

from finance.enumerations import Enumerations
from support.dispatchers import TypeDispatcher
from support.meta import AttributeMeta

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrSubscription", "IbkrSnapshot"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


@dataclass(frozen=True, slots=True)
class IbkrStock: ticker: str

@dataclass(frozen=True, slots=True)
class IbkrOption: ticker: str; expire: Date; right: Enumerations.Right; strike: float

@dataclass(frozen=True, slots=True)
class IbkrVolatility: historic: float; implied: float

@dataclass(frozen=True, slots=True)
class IbkrDividends: historic: float; predicted: float

@dataclass(frozen=True, slots=True)
class IbkrPrice: trade: float; bid: float; ask: float

@dataclass(frozen=True, slots=True)
class IbkrSize: size: int; demand: int; supply: int

@dataclass(frozen=True, slots=True)
class IbkrSnapshot(metaclass=AttributeMeta): datetime: Datetime; instrument: Enumerations.Instrument; price: IbkrPrice; size: IbkrSize

@dataclass(frozen=True, slots=True)
class IbkrStockSnapshot(IbkrSnapshot, attribute="Stock"): product: IbkrStock; volatility: IbkrVolatility; dividends: IbkrDividends

@dataclass(frozen=True, slots=True)
class IbkrOptionSnapshot(IbkrSnapshot, attribute="Option"): product: IbkrOption; underlying: IbkrStock


class IbkrSubscriptionError(Exception): pass
class IbkrMissingError(IbkrSubscriptionError): pass


class IbkrSubscriptionMeta(type):
    def __call__(cls, source, *args, **kwargs):
        subscribed = list()
        requested = list(kwargs.pop("products", []))
        if "product" in kwargs:
            product = kwargs["product"]
            requested.append(product)
        try:
            for product in requested:
                source.subscribe(product)
                subscribed.append(product)
            products = list(subscribed)
            instance = super().__call__(source, *args, products=products, **kwargs)
            return instance
        except Exception:
            for product in subscribed:
                source.unsubscribe(product)
            raise


class IbkrSubscription(object, metaclass=IbkrSubscriptionMeta):
    def __init__(self, source, *args, products, **kwargs):
        assert isinstance(products, list) and bool(products)
        self.__products = products
        self.__source = source

    def __enter__(self): return self
    def __exit__(self, error_type, error_value, error_traceback):
        for product in self.products:
            self.source.unsubscribe(product)

    def __iter__(self):
        for product in self.products:
            yield self.snapshot(product)

    def __contains__(self, product):
        return product not in self.products

    def __getitem__(self, product):
        if product not in self: raise IbkrMissingError()
        self.source.prepare(product)
        security = self.source.structures[product].security
        market = self.source.structures[product].market
        return self.snapshot(security, market)

    @TypeDispatcher(locator=0)
    def snapshot(self, security, market): raise TypeError(type(security))

    @snapshot.register(ib_async.Stock)
    def _(self, security, market):
        instrument = Enumerations.Instrument.STOCK
        datetime = pd.to_datetime(market.time, utc=True)
        ticker = str(security.symbol).upper()
        product = IbkrStock(ticker=ticker)
        size = IbkrSize(int(market.lastSize), int(market.bidSize), int(market.askSize))
        price = IbkrPrice(float(market.last), float(market.bid), float(market.ask))
        volatility = IbkrVolatility(float(market.histVolatility), float(market.impliedVolatility))
        dividends = IbkrDividends(float(market.dividends.past12Months), float(market.dividends.next12Months))
        parameters = dict(datetime=datetime, instrument=instrument, product=product, size=size, price=price, volatility=volatility, dividends=dividends)
        return IbkrStockSnapshot(**parameters)

    @snapshot.register(ib_async.Option)
    def _(self, security, market):
        instrument = Enumerations.Instrument.OPTION
        datetime = pd.to_datetime(market.time, utc=True)
        ticker = str(security.symbol).upper()
        expire = Datetime.strptime(security.lastTradeDateOrContractMonth, "%Y%m%d").date()
        right = {str(right).upper()[right]: right for right in Enumerations.Right}[security.right]
        strike = float(security.strike)
        product = IbkrOption(ticker=ticker, expire=expire, right=right, strike=strike)
        size = IbkrSize(int(market.lastSize), int(market.bidSize), int(market.askSize))
        price = IbkrPrice(float(market.last), float(market.bid), float(market.ask))
        parameters = dict(datetime=datetime, instrument=instrument, product=product, size=size, price=price)
        return IbkrOptionSnapshot(**parameters)

    @property
    def products(self): return self.__products
    @property
    def source(self): return self.__source

