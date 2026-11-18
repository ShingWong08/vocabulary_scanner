import pytest

from vocabulary_scanner.cefrDictionary import CefrDictionary, getTokenCandidates, normalize, sortLevels


class FakeLemmatizer:
    def lemmatize(self, word, pos):
        if word == "ran" and pos == "v":
            return "run"
        return word


def test_normalize_lowercases_and_removes_accents():
    assert normalize("Café-Owner's!") == "cafe-owner's"
    assert normalize("  Climate   Change ") == "climate change"


def test_sort_levels_drops_invalid_levels():
    assert sortLevels(["C1", "", "B2", "C1", "X"]) == ("B2", "C1")


def test_lowest_level_is_the_main_level(dictionary):
    hit = dictionary.lookupWord("Ambiguous")
    assert hit.word == "ambiguous"
    assert hit.level == "B2"
    assert hit.allLevels == ("B2", "C1")
    assert hit.partsOfSpeech == ("adjective",)


def test_unknown_word_returns_none(dictionary):
    assert dictionary.lookupWord("qwzx") is None


def test_lemmatizer_finds_base_form(dictionary):
    assert dictionary.lookupWord("ran") is None
    assert dictionary.lookupWord("ran", FakeLemmatizer()).word == "run"


def test_adverb_falls_back_to_adjective(dictionary):
    assert dictionary.lookupWord("coherently").word == "coherent"


def test_hyphen_can_be_removed():
    assert getTokenCandidates("e-mail") == ["e-mail", "email"]


def test_phrase_lookup(dictionary):
    hit = dictionary.lookupPhrase("Climate  Change")
    assert hit.word == "climate change"
    assert hit.level == "B2"
    assert dictionary.lookupPhrase("climate crisis") is None


def test_missing_dictionary_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        CefrDictionary(str(tmp_path / "missing.csv"))


def test_word_without_hyphen_finds_hyphenated_entry(dictionary):
    hit = dictionary.lookupWord("wellbeing")
    assert hit.word == "well-being"
    assert hit.level == "B2"


def test_estimated_dictionary_is_only_a_fallback(dictionaryWithEstimates):
    addictive = dictionaryWithEstimates.lookupWord("addictive")
    assert addictive.level == "B2"
    assert addictive.estimated is True

    cat = dictionaryWithEstimates.lookupWord("cat")
    assert cat.level == "A1"
    assert cat.estimated is False


def test_is_estimated_word(dictionaryWithEstimates):
    assert dictionaryWithEstimates.isEstimatedWord("addictive") is True
    assert dictionaryWithEstimates.isEstimatedWord("cat") is False  # main dictionary wins
    assert dictionaryWithEstimates.isEstimatedWord("qwzx") is False


def test_estimated_dictionary_can_be_turned_off(dictionaryPath, estimatedPath):
    assert CefrDictionary(dictionaryPath, estimatedPath=None).lookupWord("addictive") is None


def test_missing_estimated_file_is_ignored(dictionaryPath, tmp_path):
    dictionary = CefrDictionary(dictionaryPath, estimatedPath=str(tmp_path / "missing.csv"))
    assert dictionary.lookupWord("addictive") is None


def test_bundled_dictionary_loads():
    dictionary = CefrDictionary()
    assert dictionary.lookupWord("cat").level == "A1"
    assert dictionary.lookupWord("ambiguous") is not None
    assert dictionary.lookupWord("costeffective").word == "cost-effective"
    assert dictionary.lookupWord("tonne").level == "B2"  # new in CEFR-J 1.6
    assert dictionary.lookupWord("wellbeing").estimated is True  # not in CEFR-J / Octanove
    assert dictionary.lookupWord("addictive").estimated is True
    assert dictionary.lookupWord("woodward") is None  # names are filtered out of the estimates
