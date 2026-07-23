"""
research/ — 架构研究算法 (非电路实现, 不进入 Phase 2 Entry Gate)
=================================================================

本目录包含探索性搜索算法, 用于将"算法上限"与"物理 DAC 上限"分离。
这些算法不是 VA/电路中实际使用的方案, 仅用于诊断和分析。

模块:
  codebook_search — CodebookNearestSearch (原 BinarySearchSAR)
"""

from .codebook_search import CodebookNearestSearch

__all__ = ["CodebookNearestSearch"]
