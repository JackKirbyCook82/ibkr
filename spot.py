# -*- coding: utf-8 -*-
"""
Created on Fri Oct 16 2026
@name:   Ikbr Spot Objects
@author: Jack Kirby Cook
@file:   ikbr/spot.py

"""

from abc import ABC

from ibkr.website import IbkrPage, IbkrDownloader

__version__ = "1.0.0"
__author__ = "Jack Kirby Cook"
__all__ = []
__copyright__ = "Copyright 2026, Jack Kirby Cook"
__license__ = "MIT License"


class IbkrSpotPage(IbkrPage, ABC):
    pass


class IbkrSpotDownloader(IbkrDownloader):
    pass



