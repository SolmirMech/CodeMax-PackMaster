# data_providers/__init__.py
from .base_provider import BaseDataProvider
from .workshop1_provider import Workshop1DataProvider
from .workshop2_provider import Workshop2DataProvider

__all__ = [
    'BaseDataProvider',
    'Workshop1DataProvider',
    'Workshop2DataProvider'
]