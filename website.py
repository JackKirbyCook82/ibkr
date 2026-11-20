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
from abc import ABC
from ib_async import util
from dataclasses import dataclass
from types import SimpleNamespace
from datetime import datetime as Datetime

from finance.enumerations import Enumerations
from webscraping.webpages import WebSOCKPage
from support.dispatchers import ValueDispatcher
from support.mixins import LoggingMixin
from support.meta import CollectionMeta, NamespaceMeta

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrPage", "IbkrStream"]
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
class IbkrFrequency: by: Enumerations.Frequency; code: str; span: list[int]
class IbkrFrequencies(metaclass=CollectionMeta):
    minutes = IbkrFrequency(Enumerations.Frequency.MINUTELY, "min", [1, 2, 3, 5, 10, 15, 20, 30])
    hours = IbkrFrequency(Enumerations.Frequency.HOURLY, "hour", [1, 2, 3, 4, 8])
    months = IbkrFrequency(Enumerations.Frequency.MONTHLY, "month", [1])
    weeks = IbkrFrequency(Enumerations.Frequency.WEEKLY, "week", [1])
    days = IbkrFrequency(Enumerations.Frequency.DAILY, "day", [1])

    def __new__(cls, frequency):
        by, span = frequency.by, frequency.span
        frequencies = {frequency.by: frequency for frequency in dict(cls).values()}
        if by not in frequencies.keys(): raise IbkrFrequencyByError()
        if span not in frequencies[by].span: raise IbkrFrequencySpanError()
        return f"{int(span)} {str(frequencies[by].code)}{'s' if span > 1 else ''}"


class IbkrPage(WebSOCKPage):
    def securities(self, *args, security, settlements, **kwargs):
        parameters = dict(underlyingSymbol=security.symbol, futFopExchange="", underlyingSecType="STK", underlyingConId=security.conId)
        chains = self.source.connection.reqSecDefOptParams(**parameters)
        chain = next(chain for chain in chains if chain.exchange == "SMART")
        expires = [Datetime.strptime(expire, "%Y%m%d").date() for expire in chain.expirations]
        strikes = list(map(float, chain.strikes))
        settlements = [SimpleNamespace(expire=expire, strike=strike) for expire in expires for strike in strikes if (expire, strike) in settlements]
        settlements.sort(key=lambda settlement: (settlement.expire, settlement.strike))
        settlements = [SimpleNamespace(expire=settlement.expire, strike=settlement.strike, right=str(right).upper()[0]) for right in list(Enumerations.Right) for settlement in settlements]
        parameters = dict(symbol=security.symbol, exchange=chain.exchange, currency="USD", multiplier=chain.multiplier, tradingClass=chain.tradingClass)
        function = lambda settlement: ib_async.Option(**parameters, lastTradeDateOrContractMonth=settlement.expire.strftime("%Y%m%d"), strike=settlement.strike, right=settlement.right)
        securities = list(map(function, settlements))
        if not securities: return []
        securities = self.source.qualify(securities, certify=False)
        return securities

    def bars(self, *args, security, stop, **kwargs):
        frequency = self.frequency(*args, **kwargs)
        duration = self.duration(*args, **kwargs)
        price = self.price(*args, **kwargs)
        parameters = dict(whatToShow=price, endDateTime=stop, durationStr=duration, barSizeSetting=frequency, useRTH=True)
        records = self.source.connection.reqHistoricalData(security, **parameters)
        dataframe = util.df(records)
        return dataframe

    def ticks(self, *args, security, stop, sparse=False, **kwargs):
        price = self.price(*args, **kwargs)
        parameters = dict(whatToShow=price, startDateTime="", endDateTime=stop, numberOfTicks=1000, useRTH=True, ignoreSize=not sparse)
        records = self.source.connection.reqHistoricalTicks(security, **parameters)
        dataframe = util.df(records)
        return dataframe

    @ValueDispatcher(locator="instrument")
    def spot(self, *args, instrument, **kwargs): raise ValueError(instrument)

    @spot.register(Enumerations.Instrument.STOCK)
    def _(self, *args, security, **kwargs):
        market = self.source.connection.reqTickers(security)
        security = market.contract
        instrument = Enumerations.Instrument.STOCK
        datetime = pd.to_datetime(market.time, utc=True)
        ticker = str(security.symbol).upper()
        product = {"ticker": ticker}
        trade = {"price": market.last, "size": market.lastSize}
        quote = {"bid": market.bid, "ask": market.ask, "demand": market.bidSize, "supply": market.askSize}
        price = (market.bid + market.ask) / 2
        volatility = float(market.impliedVolatility)
        dividends = np.log1p(float(market.dividends.next12Months) / price)
        underlying = {"volatility": volatility, "dividends": dividends}
        records = {"instrument": instrument, "datetime": datetime} | product | trade | quote | underlying
        dataframe = pd.DataFrame.from_records([records])
        return dataframe

    @spot.register(Enumerations.Instrument.OPTION)
    def _(self, *args, security, **kwargs):
        market = self.source.connection.reqTickers(security)
        security = market.contract
        instrument = Enumerations.Instrument.OPTION
        datetime = pd.to_datetime(market.time, utc=True)
        ticker = str(security.symbol).upper()
        expire = Datetime.strptime(security.lastTradeDateOrContractMonth, "%Y%m%d").date()
        right = {str(right).upper()[right]: right for right in Enumerations.Right}[security.right]
        strike = float(security.strike)
        product = {"ticker": ticker, "expire": expire, "right": right, "strike": strike}
        trade = {"price": market.last, "size": market.lastSize}
        quote = {"bid": market.bid, "ask": market.ask, "demand": market.bidSize, "supply": market.askSize}

#        underlying = (market.bid + market.ask) / 2
#        volatility = float(market.impliedVolatility)
#        dividends = np.log1p(float(market.dividends.next12Months) / underlying)
#        underlying = {"underlying": underlying, "volatility": volatility, "dividends": dividends}

        records = {"instrument": instrument, "datetime": datetime} | product | trade | quote
        dataframe = pd.DataFrame.from_records([records])
        return dataframe

    @staticmethod
    def price(*args, price, **kwargs): return {Enumerations.Price.TRADE: "TRADES", Enumerations.Price.MID: "MIDPOINT", Enumerations.Price.BID: "BID", Enumerations.Price.ASK: "ASK", Enumerations.Price.QUOTE: "BID_ASK"}[price]
    @staticmethod
    def duration(*args, duration, **kwargs): return f"{int(duration.total_seconds())} S"
    @staticmethod
    def frequency(*args, frequency, **kwargs): return IbkrFrequencies(frequency)


class IbkrStream(LoggingMixin, ABC, namespace={"instrument": None, "price": None, "page": None, "limit": 80}, metaclass=NamespaceMeta):
    def __init_subclass__(cls, **kwargs): pass
    def __init__(self, *args, instrument, price, limit, page, **kwargs):
        super().__init__(*args, **kwargs)
        self.__page = page(*args, **kwargs)
        self.__instrument = instrument
        self.__price = price
        self.__limit = limit

    @property
    def instrument(self): return self.__instrument
    @property
    def price(self): return self.__price
    @property
    def limit(self): return self.__limit
    @property
    def page(self): return self.__page



