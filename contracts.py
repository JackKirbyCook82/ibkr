# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Contract Objects
@author: Jack Kirby Cook
@file:   ibkr/contracts.py

"""

from ib_async import Stock, Option
from itertools import product as iterprod
from datetime import datetime as Datetime

from ibkr.website import IbkrPage
from finance.enumerations import Option
from finance.querys import Symbol, Contract

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = []
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IkbrContractPage(IbkrPage):
    def __call__(self, *args, product, expires, strikes, **kwargs):
        assert expires is not None and bool(expires)
        assert strikes is not None and bool(strikes)
        if isinstance(product, Stock): security = product
        elif isinstance(product, Symbol):
            try: security = product["security"]
            except KeyError: security = self.security(product)
        else: raise TypeError(product)
        if not bool(security.conId): security = self.qualify(security)
        parameters = dict(security=security, expires=expires, strikes=strikes)
        contracts = self.execute(**parameters)
        return contracts

    def execute(self, *args, **kwargs):
        securities = list(self.securities(*args, **kwargs))
        securities = self.qualify(securities)
        contracts = self.contracts(securities)
        return contracts

    def securities(self, *args, security, expires, strikes, **kwargs):
        parameters = dict(underlyingSymbol=security.symbol, futFopExchange="", underlyingSecType="STK", underlyingConId=security.conId)
        chain = self.source.connection.reqSecDefOptParams(**parameters)
        expires = [expire for expire in chain.expirations if Datetime.strptime(expire, "%Y%m%d").date() in expires]
        strikes = [strike for strike in chain.strikes if float(strike) in strikes]
        options = [str(option).upper()[0] for option in list(Option)]
        parameters = dict(symbol=security.symbol, exchange=chain.exchange, currency="USD", multiplier=chain.multiplier, tradingClass=chain.tradingClass)
        for expire, strike, option in iterprod(expires, strikes, options):
            yield Option(**parameters, lastTradeDateOrContractMonth=expire, strike=strike, option=option)

    @staticmethod
    def contracts(securities):
        for security in securities:
            ticker = str(security.symbol).upper()
            expire = Datetime.strptime(security.lastTradeDateOrContractMonth, "%Y%m%d").date()
            option = {str(option).upper()[0]: option for option in list(Option)}[security.right]
            strike = float(security.strike)
            contract = Contract(ticker, expire, strike, option)
            contract["security"] = security
            yield contract



