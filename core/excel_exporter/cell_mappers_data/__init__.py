# cell_mappers_data/__init__.py
"""Импорты данных маппингов"""

from .workshop1_box import (
    STATIC_CELLS as WORKSHOP1_BOX_STATIC,
    DYNAMIC_SECTIONS as WORKSHOP1_BOX_DYNAMIC
)

__all__ = [
    'WORKSHOP1_BOX_STATIC',
    'WORKSHOP1_BOX_DYNAMIC',
]