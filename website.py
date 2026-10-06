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
from support.mixins import Logging

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = []
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrAPI(object):
    @singledispatchmethod
    @staticmethod
    def security(product): raise TypeError(type(product))

    @security.register(Contract)
    @staticmethod
    def contract(contract): return Option(contract.ticker, contract.expire.strftime("%Y%m%d"), contract.strike, str(contract.option).upper()[0], "SMART")

    @security.register(Symbol)
    @staticmethod
    def symbol(symbol): return Stock(symbol.ticker, "SMART", "USD")


class IbkrPage(WebSOCKPage):
    pass


class IbkrDownloader(Results, Logging, ABC):
    pass


#
#

