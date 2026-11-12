"""spaCy sentence analysis (spaCy 3.8 + ``en_core_web_sm`` 3.8.0; 7.1 section 25.3).

The model is loaded once per process, on first use, and shared: workers fork
before using it (Celery prefork), and loading takes about half a second. It
runs on CPU and is deterministic for a given model version.
"""

from collections.abc import Sequence
from functools import cache
from importlib.metadata import version
from typing import Any

import spacy

from memory_engine.personal.application.analysis import Sentence, Token

MODEL = "en_core_web_sm"


@cache
def _pipeline() -> Any:
    return spacy.load(MODEL)


class SpacySentenceAnalyzer:
    @property
    def version(self) -> str:
        meta = _pipeline().meta
        return f"spacy-{version('spacy')}/{meta['lang']}_{meta['name']}-{meta['version']}"

    def analyze(self, text: str) -> Sequence[Sentence]:
        document = _pipeline()(text)
        sentences: list[Sentence] = []
        for index, span in enumerate(document.sents):
            start = span.start
            tokens = [
                Token(
                    text=token.text,
                    lower=token.lower_,
                    lemma=token.lemma_.lower(),
                    pos=token.pos_,
                    dep=token.dep_,
                    head=token.head.i - start,
                    entity=token.ent_type_,
                    is_stop=bool(token.is_stop),
                )
                for token in span
                if not token.is_space
            ]
            if tokens:
                sentences.append(Sentence(index=index, text=span.text.strip(), tokens=tokens))
        return sentences
