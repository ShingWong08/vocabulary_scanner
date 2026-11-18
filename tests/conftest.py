import pytest

from vocabulary_scanner.cefrDictionary import CefrDictionary


DICTIONARY_ROWS = [
    "word,pos,level,type",
    "ambiguous,adjective,C1,word",
    "ambiguous,adjective,B2,word",
    "cat,noun,A1,word",
    "run,verb,A1,word",
    "coherent,adjective,C1,word",
    "well-being,noun,B2,word",
    "climate,noun,B1,word",
    "change,noun,A2,word",
    "climate change,noun,B2,phrase",
    "according to,preposition,B1,phrase",
]

ESTIMATED_ROWS = [
    "word,level",
    "addictive,B2",
    "alertness,C1",
    "cat,C2",  # also in the main dictionary, which must win
]


@pytest.fixture
def dictionaryPath(tmp_path):
    path = tmp_path / "cefr_words.csv"
    path.write_text("\n".join(DICTIONARY_ROWS) + "\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def estimatedPath(tmp_path):
    path = tmp_path / "cefr_words_estimated.csv"
    path.write_text("\n".join(ESTIMATED_ROWS) + "\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def dictionary(dictionaryPath):
    return CefrDictionary(dictionaryPath, estimatedPath=None)


@pytest.fixture
def dictionaryWithEstimates(dictionaryPath, estimatedPath):
    return CefrDictionary(dictionaryPath, estimatedPath)
