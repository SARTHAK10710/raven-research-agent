"""NLP adapters (7.1 section 25.3): spaCy with ``en_core_web_sm``, English first (G6).

Only this package imports spaCy (tested). Application code depends on the
``SentenceAnalyzer`` port in ``memory_engine.personal.application.analysis``.
"""

from memory_engine.infrastructure.nlp.spacy_analyzer import SpacySentenceAnalyzer

__all__ = ["SpacySentenceAnalyzer"]
