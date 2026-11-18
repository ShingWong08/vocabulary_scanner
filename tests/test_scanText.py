from vocabulary_scanner.scanText import (
    MAX_EXAMPLE_LENGTH,
    PHRASE_KIND,
    WORD_KIND,
    ScanResult,
    VocabularyEntry,
    mergeEntries,
    scanText,
    splitSentences,
)


def test_hard_wrapped_lines_stay_in_one_sentence():
    text = "The cat sat\non the mat. It ran away!\n\nNew paragraph"
    assert splitSentences(text) == ["The cat sat on the mat.", "It ran away!", "New paragraph"]


def test_windows_line_breaks_do_not_split_sentences():
    assert splitSentences("The cat sat\r\non the mat.") == ["The cat sat on the mat."]


def test_long_sentences_are_shortened():
    sentence = splitSentences("word " * 100)[0]
    assert len(sentence) <= MAX_EXAMPLE_LENGTH + 1
    assert sentence.endswith("…")


def test_sentences_without_letters_are_skipped():
    assert splitSentences("123. 456.") == []


def test_links_and_emails_are_removed():
    text = "See https://doi.org/10.1037/abc and www.example.com or mail me@uni.edu today."
    assert splitSentences(text) == ["See and or mail today."]


def test_estimated_words_are_marked(dictionaryWithEstimates):
    result = scanText("Social media is addictive for a cat.", dictionaryWithEstimates)

    assert result.entries[("addictive", WORD_KIND)].estimated is True
    assert result.entries[("cat", WORD_KIND)].estimated is False
    assert result.levelTokenCounts["B2"] == 1


def test_scan_counts_words_levels_and_unknown_words(dictionary):
    result = scanText("The cat is ambiguous. The CAT is a cat.", dictionary, sourceLabel="a.txt")

    cat = result.entries[("cat", WORD_KIND)]
    assert cat.count == 3
    assert cat.sources == {"a.txt"}
    assert cat.example == "The cat is ambiguous."

    assert result.levelTokenCounts["A1"] == 3
    assert result.levelTokenCounts["B2"] == 1
    assert result.unknownWords["the"] == 2
    assert result.totalTokens == 9
    assert result.totalUniqueWords == 5  # cat, ambiguous, the, is, a


def test_phrases_are_found_once(dictionary):
    result = scanText("Climate change matters, according to experts.", dictionary)

    assert result.entries[("climate change", PHRASE_KIND)].count == 1
    assert result.entries[("according to", PHRASE_KIND)].count == 1
    # Words inside a phrase are still counted as words
    assert result.entries[("climate", WORD_KIND)].count == 1


def test_scan_results_can_be_merged(dictionary):
    total = ScanResult()
    total.merge(scanText("A cat.", dictionary, sourceLabel="a.txt"))
    total.merge(scanText("Another cat.", dictionary, sourceLabel="b.txt"))

    cat = total.entries[("cat", WORD_KIND)]
    assert cat.count == 2
    assert cat.sources == {"a.txt", "b.txt"}
    assert cat.example == "A cat."
    assert total.levelUniqueWords["A1"] == {"cat"}


def test_merge_entries_keeps_existing_details():
    old = {("cat", WORD_KIND): VocabularyEntry("cat", "A1", ("A1",), ("noun",), WORD_KIND, 2, {"a"}, "Old.", "", "貓")}
    new = {("cat", WORD_KIND): VocabularyEntry("cat", "A1", ("A1", "B1"), ("noun",), WORD_KIND, 1, {"b"}, "New.", "a pet", "")}

    merged = mergeEntries(old, new)[("cat", WORD_KIND)]

    assert merged.count == 3
    assert merged.sources == {"a", "b"}
    assert merged.example == "Old."
    assert merged.definition == "a pet"
    assert merged.translation == "貓"
    assert merged.allLevels == ("A1", "B1")
