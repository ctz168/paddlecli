#!/usr/bin/env python3
"""
Jupyter Notebook Parser

Parse .ipynb files and extract code/markdown cells.
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class CellType(Enum):
    """Cell types in Jupyter Notebook"""
    CODE = "code"
    MARKDOWN = "markdown"
    RAW = "raw"


@dataclass
class NotebookCell:
    """Represents a single cell in a Jupyter Notebook"""
    index: int
    cell_type: CellType
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_count: Optional[int] = None
    outputs: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_code(self) -> bool:
        return self.cell_type == CellType.CODE

    @property
    def is_markdown(self) -> bool:
        return self.cell_type == CellType.MARKDOWN

    @property
    def is_raw(self) -> bool:
        return self.cell_type == CellType.RAW

    def get_source_lines(self) -> List[str]:
        """Get source as list of lines"""
        return self.source.split('\n')

    def has_magic_commands(self) -> bool:
        """Check if cell contains IPython magic commands"""
        lines = self.get_source_lines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('%') or stripped.startswith('!'):
                return True
        return False

    def get_magic_commands(self) -> List[str]:
        """Extract magic commands from cell"""
        magics = []
        lines = self.get_source_lines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('%%'):
                # Cell magic - entire cell
                magics.append(('cell', stripped))
            elif stripped.startswith('%'):
                # Line magic
                magics.append(('line', stripped))
            elif stripped.startswith('!'):
                # Shell command
                magics.append(('shell', stripped))
        return magics

    def __repr__(self) -> str:
        return f"NotebookCell(index={self.index}, type={self.cell_type.value}, lines={len(self.get_source_lines())})"


@dataclass
class Notebook:
    """Represents a Jupyter Notebook"""
    path: Path
    cells: List[NotebookCell]
    metadata: Dict[str, Any] = field(default_factory=dict)
    nbformat: int = 4
    nbformat_minor: int = 0

    @property
    def code_cells(self) -> List[NotebookCell]:
        """Get all code cells"""
        return [c for c in self.cells if c.is_code]

    @property
    def markdown_cells(self) -> List[NotebookCell]:
        """Get all markdown cells"""
        return [c for c in self.cells if c.is_markdown]

    def get_cell(self, index: int) -> Optional[NotebookCell]:
        """Get cell by index"""
        for cell in self.cells:
            if cell.index == index:
                return cell
        return None

    def get_code_cells_by_tag(self, tag: str) -> List[NotebookCell]:
        """Get code cells with a specific tag"""
        result = []
        for cell in self.code_cells:
            tags = cell.metadata.get('tags', [])
            if tag in tags:
                result.append(cell)
        return result

    def __repr__(self) -> str:
        return f"Notebook(path={self.path}, cells={len(self.cells)}, code_cells={len(self.code_cells)})"


class NotebookParser:
    """Parse Jupyter Notebook files"""

    @staticmethod
    def parse_file(filepath: Union[str, Path]) -> Notebook:
        """Parse a .ipynb file"""
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Notebook not found: {filepath}")

        if filepath.suffix != '.ipynb':
            raise ValueError(f"Not a Jupyter Notebook file: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)

        return NotebookParser.parse_dict(content, filepath)

    @staticmethod
    def parse_dict(data: Dict[str, Any], path: Optional[Path] = None) -> Notebook:
        """Parse notebook data from dictionary"""
        # Get notebook metadata
        metadata = data.get('metadata', {})
        nbformat = data.get('nbformat', 4)
        nbformat_minor = data.get('nbformat_minor', 0)

        # Parse cells
        cells = []
        raw_cells = data.get('cells', [])

        for idx, raw_cell in enumerate(raw_cells):
            cell = NotebookParser._parse_cell(idx, raw_cell)
            cells.append(cell)

        return Notebook(
            path=path or Path('<memory>'),
            cells=cells,
            metadata=metadata,
            nbformat=nbformat,
            nbformat_minor=nbformat_minor
        )

    @staticmethod
    def _parse_cell(index: int, raw_cell: Dict[str, Any]) -> NotebookCell:
        """Parse a single cell from raw data"""
        cell_type_str = raw_cell.get('cell_type', 'code')
        try:
            cell_type = CellType(cell_type_str)
        except ValueError:
            cell_type = CellType.CODE

        # Parse source - can be string or list of strings
        raw_source = raw_cell.get('source', '')
        if isinstance(raw_source, list):
            source = ''.join(raw_source)
        else:
            source = raw_source

        # Remove trailing newline if present (Jupyter style)
        if source.endswith('\n'):
            source = source[:-1]

        return NotebookCell(
            index=index,
            cell_type=cell_type,
            source=source,
            metadata=raw_cell.get('metadata', {}),
            execution_count=raw_cell.get('execution_count'),
            outputs=raw_cell.get('outputs', [])
        )

    @staticmethod
    def extract_code(notebook: Notebook, skip_markdown: bool = True) -> str:
        """Extract all code from notebook as a single Python script"""
        lines = []

        for cell in notebook.cells:
            if cell.is_code:
                # Add cell separator comment
                lines.append(f"# {'='*60}")
                lines.append(f"# Cell {cell.index}")
                lines.append(f"# {'='*60}")
                lines.append("")
                lines.append(cell.source)
                lines.append("")
            elif not skip_markdown and cell.is_markdown:
                # Add markdown as comments
                lines.append(f"# {'='*60}")
                lines.append(f"# Markdown Cell {cell.index}")
                lines.append(f"# {'='*60}")
                for md_line in cell.get_source_lines():
                    lines.append(f"# {md_line}")
                lines.append("")

        return '\n'.join(lines)


def parse_notebook(filepath: Union[str, Path]) -> Notebook:
    """Convenience function to parse a notebook"""
    return NotebookParser.parse_file(filepath)
