# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Contract Objects
@author: Jack Kirby Cook
@file:   ibkr/contracts.py

"""

from datetime import datetime as Datetime

from ibkr.website import IbkrPage, IbkrStream
from finance.enumerations import Right
from finance.querys import Contract

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IbkrContractDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrContractPage(IbkrPage):
    def __call__(self, *args, product, settlements, **kwargs):
        try: security = product["security"]
        except KeyError: security = self.source.security(product)
        if not bool(security.conId): security = self.source.qualify(security)
        parameters = dict(security=security, settlements=settlements)
        contracts = self.execute(*args, **parameters, **kwargs)
        return contracts

    def execute(self, *args, **kwargs):
        securities = self.securities(*args, **kwargs)
        contracts = self.contracts(securities, *args, **kwargs)
        return list(contracts)

    @staticmethod
    def contracts(securities, *args, **kwargs):
        for security in securities:
            ticker = str(security.symbol).upper()
            expire = Datetime.strptime(security.lastTradeDateOrContractMonth, "%Y%m%d").date()
            right = {str(right).upper()[0]: right for right in list(Right)}[security.right]
            strike = float(security.strike)
            contract = Contract(ticker, expire, right, strike)
            contract["security"] = security
            yield contract


class IbkrContractDownloader(IbkrStream, page=IbkrContractPage):
    def __call__(self, products, /, **kwargs):
        if not isinstance(products, list): products = [products]
        if not bool(products): return None
        contracts = self.downloader(products, **kwargs)
        contracts = list(contracts)
        if not contracts: return None
        contracts.sort(key=lambda contract: (contract.ticker, contract.expire))
        return contracts

    def downloader(self, products, /, **kwargs):
        for product in products:
            contracts = self.page(product=product, **kwargs)
            yield from iter(contracts)



