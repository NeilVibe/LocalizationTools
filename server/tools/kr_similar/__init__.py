"""
KR Similar - Korean Semantic Similarity Search Tool

App #3 in the LocaNext platform.

Provides:
- Korean string similarity search using BERT embeddings
- Dictionary creation from translation files (BDO/BDM format)
- Similar string extraction for quality checks
- Auto-translation using semantic matching

Uses the same Korean BERT model as XLSTransfer:
    snunlp/KR-SBERT-V40K-klueNLI-augSTS (447MB)
"""

from server.tools.kr_similar.core import KRSimilarCore
from server.tools.kr_similar.embeddings import EmbeddingsManager
from server.tools.kr_similar.searcher import SimilaritySearcher

__all__ = ['KRSimilarCore', 'EmbeddingsManager', 'SimilaritySearcher']
