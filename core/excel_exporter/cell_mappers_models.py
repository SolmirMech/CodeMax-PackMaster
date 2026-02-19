# cell_mappers_models.py
"""Базовые классы для маппингов (вынесены отдельно)"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

class DataType(Enum):
    TEXT = "text"
    NUMBER = "number"
    INTEGER = "integer"
    DATE = "date"
    MULTILINE_TEXT = "multiline_text"
    FORMULA = "formula"

class HorizontalAlignment(Enum):
    GENERAL = "general"
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    FILL = "fill"
    JUSTIFY = "justify"
    CENTER_CONTINUOUS = "centerContinuous"
    DISTRIBUTED = "distributed"

class VerticalAlignment(Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"
    JUSTIFY = "justify"
    DISTRIBUTED = "distributed"

@dataclass
class CellFormat:
    horizontal_alignment: HorizontalAlignment = HorizontalAlignment.GENERAL
    vertical_alignment: VerticalAlignment = VerticalAlignment.CENTER
    wrap_text: bool = False
    number_format: Optional[str] = None
    font_size: Optional[int] = None
    bold: bool = False

@dataclass
class CellMapping:
    cell_reference: str
    data_key: str
    data_type: DataType
    format: CellFormat = field(default_factory=CellFormat)
    is_merged_cell: bool = False
    required: bool = False
    default_value: Any = None
    validation: Optional[Dict[str, Any]] = None

@dataclass
class DynamicSection:
    name: str
    start_cell: str
    rows_range: Tuple[int, int]
    columns_config: List[Dict[str, Any]]
    direction: str = "horizontal"
    max_items: Optional[int] = None

@dataclass
class SheetMapping:
    sheet_name: str
    workshop: str
    description: str
    static_cells: List[CellMapping]
    dynamic_sections: List[DynamicSection]
    post_processing_hooks: List[str] = field(default_factory=list)