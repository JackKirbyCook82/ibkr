# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Contract Objects
@author: Jack Kirby Cook
@file:   ibkr/contracts.py

"""

from ibkr.website import IbkrPage, IbkrDownloader
from datetime import datetime as Datetime

from finance.enumerations import Right, Instrument
from finance.querys import Contract

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrContractDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrContractPage(IbkrPage):
    def __call__(self, *args, product, expires, strikes, **kwargs):
        assert expires is not None and bool(expires)
        assert strikes is not None and bool(strikes)
        try: security = product["security"]
        except KeyError: security = self.source.security(product)
        if not bool(security.conId): security = self.source.qualify(security)
        parameters = dict(security=security, expires=expires, strikes=strikes)
        contracts = self.execute(**parameters)
        return contracts

    def execute(self, *args, **kwargs):
        chain = self.chain(*args, **kwargs)
        contracts = self.contracts(chain, *args, **kwargs)
        return list(contracts)

    @staticmethod
    def contracts(chain, *args, **kwargs):
        for security in chain:
            ticker = str(security.symbol).upper()
            expire = Datetime.strptime(security.lastTradeDateOrContractMonth, "%Y%m%d").date()
            right = {str(right).upper()[0]: right for right in list(Right)}[security.right]
            strike = float(security.strike)
            contract = Contract(ticker, expire, strike, right)
            contract["security"] = security
            yield contract


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
            scope = self.scope(contracts)
            results = self.results(scope=scope, size=len(contracts))
            self.console("Downloaded", results)
            for contract in contracts: yield contract




