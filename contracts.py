# -*- coding: utf-8 -*-
"""
Created on Sun Oct 4 2026
@name:   IBKR Contract Objects
@author: Jack Kirby Cook
@file:   ibkr/contracts.py

"""

from finance.reporting import Results
from support.mixins import Logging

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = ["IKBRContractDownloader"]
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IKBRContractPage():
    def __call__(self, *args, **kwargs):
        pass

    def execute(self, *args, **kwargs):
        pass


class IKBRContractDownloader(Results, Logging):
    def __init__(self, *args, **kwargs):
        self.__page = IKBRContractPage(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def __call__(self, products, /, **kwargs):
        pass

    def downloader(self, products, /, **kwargs):
        pass

    @property
    def page(self): return self.__page
