import csv

from vocabulary_scanner.buildDictionary import buildDictionary, buildEstimatedDictionary, expandHeadword, main, toCefrLevel


def writeCSV(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(header)
        writer.writerows(rows)


def test_expand_headword():
    assert expandHeadword("agonize/agonise") == ["agonize", "agonise"]
    assert expandHeadword("a.m./A.M./am/AM") == ["am"]


def test_build_dictionary_merges_sources(tmp_path):
    cefrj = tmp_path / "cefrj.csv"
    octanove = tmp_path / "octanove.csv"
    writeCSV(cefrj, ["headword", "pos", "CEFR"], [["story/storey", "noun", "A1"], ["climate change", "noun", "B2"], ["bad", "noun", "X"]])
    writeCSV(octanove, ["headword", "pos", "CEFR"], [["exterior", "noun", "C1"]])

    rows = buildDictionary([str(cefrj), str(octanove)], str(tmp_path / "out.csv"))

    assert [(row["word"], row["level"], row["type"]) for row in rows] == [
        ("climate change", "B2", "phrase"),
        ("exterior", "C1", "word"),
        ("storey", "A1", "word"),
        ("story", "A1", "word"),
    ]


def test_missing_maximax_files_keep_existing_estimates(tmp_path, capsys):
    source = tmp_path / "cefrj.csv"
    writeCSV(source, ["headword", "pos", "CEFR"], [["cat", "noun", "A1"]])
    estimated = tmp_path / "estimated.csv"
    estimated.write_text("word,level\naddictive,B2\n", encoding="utf-8")

    main([str(source), "-o", str(tmp_path / "main.csv"), "--maximax-dir", str(tmp_path / "missing"),
          "--estimated-output", str(estimated)])

    assert "Skipped the estimated dictionary" in capsys.readouterr().out
    assert estimated.read_text(encoding="utf-8") == "word,level\naddictive,B2\n"


def test_to_cefr_level():
    assert toCefrLevel(1.0) == "A1"
    assert toCefrLevel(4.4) == "B2"
    assert toCefrLevel(4.5) == "C1"
    assert toCefrLevel(6.0) == "C2"
    assert toCefrLevel(9) == "C2"


def test_build_estimated_dictionary_filters_words(tmp_path):
    maximaxDir = tmp_path / "maximax"
    maximaxDir.mkdir()
    writeCSV(maximaxDir / "pos_tags.csv", ["tag_id", "tag", "description"], [["1", "NN", ""], ["2", "NNP", ""], ["3", "JJ", ""]])
    writeCSV(maximaxDir / "words.csv", ["word_id", "word", "stem_word_id"], [
        ["1", "addictive", ""],
        ["2", "california", ""],
        ["3", "cat", ""],
        ["4", "ab", ""],
        ["5", "wellbeing", ""],
        ["6", "woodward", ""],
        ["7", "covid19", ""],
    ])
    writeCSV(maximaxDir / "word_pos.csv", ["word_pos_id", "word_id", "pos_tag_id", "lemma_word_id", "frequency_count", "level"], [
        ["1", "1", "3", "", "100", "4.6"],   # adjective, kept as C1
        ["2", "1", "1", "", "100", "3.9"],   # noun use is lower, so B2 wins
        ["3", "2", "2", "", "100", "6"],     # proper noun: removed
        ["4", "3", "1", "", "100", "1"],     # in the main dictionary: removed
        ["5", "4", "1", "", "100", "2"],     # too short: removed
        ["6", "5", "1", "", "100", "6"],     # "well-being" is in the main dictionary: removed
        ["7", "6", "1", "", "100", "6"],     # not a real word (filter below): removed
        ["8", "7", "1", "", "100", "6"],     # has digits: removed
    ])

    rows = buildEstimatedDictionary(
        str(maximaxDir),
        {"cat", "well-being"},
        str(tmp_path / "estimated.csv"),
        isRealWord=lambda word: word != "woodward",
    )

    assert rows == [{"word": "addictive", "level": "B2"}]
