# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Contract Objects
@author: Jack Kirby Cook
@file:   ibkr/contracts.py

"""

import numpy as np
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime as Datetime
from collections import OrderedDict as ODict

from ibkr.website import IbkrPage, IbkrDownloader
from finance.enumerations import Right, Instrument
from finance.querys import Contract
from support.equations import Equation
from support.custom import NumberRange

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrContractDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


@dataclass(frozen=True, slots=True)
class IbkrSettlement: expire: Date; strike: float | NumberRange


class IbkrSettlementEquation(Equation, variables=["strike"]):
    forward = lambda spot, expire, today, tau, interest, dividends: spot * np.exp(np.subtract(interest, dividends) * tau(expire))
    strike = lambda forward, zscore, tau, volatility: forward * np.exp(zscore * volatility * np.sqrt(tau))
    tau = lambda expire, today: (expire - today).days / 252

    def __call__(self, *args, spot, volatility, dividends, expires, zscore, interest, **kwargs):
        parameters = dict(spot=spot, volatility=volatility, dividends=dividends, interest=interest)
        settlements = self.settlements(expires, zscore, **parameters)
        return ODict(settlements)

    def settlements(self, expires, zscore, **parameters):
        for expire in expires:
            minimum = self.evaluate(expire=expire, zscore=-zscore, **parameters)["strike"]
            maximum = self.evaluate(expire=expire, direction=+zscore, **parameters)["strike"]
            strikes = NumberRange([minimum, maximum])
            yield expire, strikes


class IbkrContractPage(IbkrPage):
    def __init__(self, *args, today, **kwargs):
        super().__init__(*args, **kwargs)
        self.__equation = IbkrSettlementEquation(today=today)

    def __call__(self, *args, product, expires, interest, **kwargs):
        assert expires is not None and bool(expires)
        try: security = product["security"]
        except KeyError: security = self.source.security(product)
        if not bool(security.conId): security = self.source.qualify(security)
        parameters = dict(security=security, expires=expires, interest=interest)
        parameters["spot"] = product["spot"]
        parameters["volatility"] = product["volatility"]
        parameters["dividends"] = product["dividends"]
        contracts = self.execute(*args, **parameters, **kwargs)
        return contracts

    def execute(self, *args, **kwargs):
        chain = self.chain(*args, **kwargs)
        expires = self.expires(chain, *args, **kwargs)
        strikes = self.strikes(chain, *args, **kwargs)
        settlements = self.settlements(expires, strikes, *args, **kwargs)
        securities = self.securities(chain, settlements, *args, **kwargs)
        contracts = self.contracts(securities, *args, **kwargs)
        return list(contracts)

    @staticmethod
    def contracts(securities, *args, **kwargs):
        for security in securities:
            ticker = str(security.symbol).upper()
            expire = Datetime.strptime(security.lastTradeDateOrContractMonth, "%Y%m%d").date()
            right = {str(right).upper()[0]: right for right in list(Right)}[security.right]
            strike = float(security.strike)
            contract = Contract(ticker, expire, strike, right)
            contract["security"] = security
            yield contract

    @property
    def equation(self): return self.__equation


class IbkrContractDownloader(IbkrDownloader, page=IbkrContractPage, instrument=Instrument.CONTRACT):
    def __call__(self, products, /, **kwargs):
        if not isinstance(products, list): products = [products]
        contracts = self.downloader(products, **kwargs)
        contracts = list(contracts)
        contracts.sort(key=lambda contract: (contract.ticker, contract.expire))
        return contracts

    def downloader(self, products, /, **kwargs):
        for product in products:
            contracts = self.page(product=product, **kwargs)
            scope = self.scope(contracts, instrument=Instrument.CONTRACT)
            results = self.results(scope=scope, size=len(contracts))
            self.console("Downloaded", results)
            for contract in contracts: yield contract




