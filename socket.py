# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Socket Objects
@author: Jack Kirby Cook
@file:   ibkr\socket.py

"""

import time
import ib_async
import numpy as np
from abc import ABCMeta
from dataclasses import dataclass
from functools import singledispatchmethod

from finance.querys import Querys
from webscraping.websources import WebSOCKSource

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrSocket"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrSocketError(Exception): pass
class IbkrSecurityError(IbkrSocketError): pass
class IbkrMarketError(IbkrSocketError): pass
class IbkrIdentityError(IbkrSocketError): pass
class IbkrLimitError(IbkrSocketError): pass


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
            if cls.instance.identity != identity: raise IbkrIdentityError()
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
            if remaining <= 0: raise IbkrMarketError(product)
            self.connection.waitOnUpdate(timeout=remaining)
        self.initialized.add(product)

    def ready(self, product):
        sanity = self.sanity(product)
        validity = self.validity(product)
        return sanity and validity

    def sanity(self, product):
        market = self.structures[product].market
        quote = np.isfinite(market.bid) and np.isfinite(market.ask)
        if product.record is not Querys.Symbol: return quote
        volatility = np.isfinite(market.impliedVolatility)
        dividends = np.isfinite(market.dividends.next12Months)
        return quote and volatility and dividends

    def validity(self, product):
        market = self.structures[product].market
        quote = 0 < market.bid <= market.ask
        if product.record is not Querys.Symbol: return quote
        volatility = market.impliedVolatility > 0
        dividends = market.dividends.next12Months >= 0
        return quote and volatility and dividends

    def subscribe(self, product):
        with self.mutex:
            try: self.structures[product].references += 1
            except KeyError:
                if self.capacity <= 0: raise IbkrLimitError()
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
        if product.record is Querys.Symbol: attributes = "104,106,456"
        elif product.record is Querys.Contract: attributes = "100,101"
        else: raise TypeError(type(product.record))
        market = self.connection.reqMktData(security, genericTickList=attributes)
        self.securities[product] = security
        return IbkrStructure(security, market)

    def destroy(self, product):
        structure = self.structures[product]
        assert structure.references == 0
        security = structure.security
        self.connection.cancelMktData(security)
        self.initialized.discard(product)

    def security(self, product):
        try:
            security = product["security"]
            self.securities[product] = security
            return security
        except KeyError: pass
        try:
            security = self.securities[product]
            return security
        except KeyError: pass
        if product.record is Querys.Symbol: return ib_async.Stock(product.ticker, "SMART", "USD")
        elif product.record is Querys.Contract: return ib_async.Option(product.ticker, product.expire.strftime("%Y%m%d"), product.strike, str(product.right).upper()[0], "SMART")
        else: raise TypeError(type(product.record))

    @singledispatchmethod
    def qualify(self, security, /, certify=True): raise TypeError(type(security))

    @qualify.register(list)
    def _(self, securities, /, certify=True):
        qualified = self.connection.qualifyContracts(*securities)
        if len(securities) != len(qualified) and bool(certify): raise IbkrSecurityError()
        if None in qualified and bool(certify): raise IbkrSecurityError()
        return qualified

    @qualify.register(ib_async.Stock)
    @qualify.register(ib_async.Option)
    def _(self, security, /, certify=True):
        qualified = self.connection.qualifyContracts(security)
        if not bool(certify): return qualified
        try: qualified = qualified[0]
        except IndexError: raise IbkrSecurityError()
        if qualified is None: raise IbkrSecurityError()
        return qualified

    @property
    def capacity(self): return self.limit - self.usage
    @property
    def usage(self): return len(self.structures)

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
