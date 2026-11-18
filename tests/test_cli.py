import json
import os

import pytest

import vocabulary_scanner as app
from vocabulary_scanner import connectWordNet, translation


@pytest.fixture(autouse=True)
def noWordNet(monkeypatch):
    monkeypatch.setattr(connectWordNet, "loadWordNet", lambda downloadIfMissing=True: (None, None))


def test_scan_sample_text(tmp_path, capsys):
    outputDir = tmp_path / "out"

    exitCode = app.main(["sample/sample_text.txt", "--out-dir", str(outputDir)])

    assert exitCode == 0
    assert sorted(os.listdir(outputDir)) == [
        "analysis_report.txt",
        "vocabulary_anki.tsv",
        "vocabulary_book.csv",
        "vocabulary_book.json",
        "vocabulary_book.xlsx",
        "vocabulary_eudic.txt",
    ]

    book = json.loads((outputDir / "vocabulary_book.json").read_text(encoding="utf-8"))
    levels = {eachEntry["level"] for eachEntry in book["entries"]}
    assert len(book["entries"]) > 0
    assert levels <= {"B2", "C1", "C2"}
    assert "Scan complete" in capsys.readouterr().out


def test_merge_adds_up_counts(tmp_path):
    outputDir = tmp_path / "out"
    app.main(["sample/sample_text.txt", "--out-dir", str(outputDir)])
    firstBook = json.loads((outputDir / "vocabulary_book.json").read_text(encoding="utf-8"))

    app.main(["sample/sample_text.txt", "--out-dir", str(outputDir), "--merge", str(outputDir / "vocabulary_book.csv")])
    secondBook = json.loads((outputDir / "vocabulary_book.json").read_text(encoding="utf-8"))

    firstCounts = {eachEntry["word"]: eachEntry["count"] for eachEntry in firstBook["entries"]}
    secondCounts = {eachEntry["word"]: eachEntry["count"] for eachEntry in secondBook["entries"]}
    assert secondCounts == {eachWord: eachCount * 2 for eachWord, eachCount in firstCounts.items()}


def test_merged_book_gets_estimated_marks_from_dictionary(dictionaryWithEstimates):
    from vocabulary_scanner.scanText import PHRASE_KIND, WORD_KIND, VocabularyEntry

    entries = [
        VocabularyEntry("addictive", "B2", ("B2",), (), WORD_KIND),
        VocabularyEntry("cat", "A1", ("A1",), (), WORD_KIND, estimated=True),
        VocabularyEntry("climate change", "B2", ("B2",), (), PHRASE_KIND),
    ]

    app.markEstimatedEntries(entries, dictionaryWithEstimates)

    assert [eachEntry.estimated for eachEntry in entries] == [True, False, False]


def test_translate_with_failures_still_writes_book(monkeypatch, tmp_path):
    requests = {}

    def fakeTranslateWords(words, language, cacheDir, translatorChoice):
        requests["language"] = language
        requests["translatorChoice"] = translatorChoice
        return {"ambiguity": "歧義"}

    monkeypatch.setattr(translation, "translateWords", fakeTranslateWords)
    outputDir = tmp_path / "out"

    exitCode = app.main(["sample/sample_text.txt", "--out-dir", str(outputDir), "--translate", "繁中", "--translator", "mymemory"])

    assert requests == {"language": "zh-TW", "translatorChoice": "mymemory"}

    assert exitCode == 0
    book = json.loads((outputDir / "vocabulary_book.json").read_text(encoding="utf-8"))
    translations = {eachEntry["word"]: eachEntry["translation"] for eachEntry in book["entries"]}
    assert translations["ambiguity"] == "歧義"


def test_lookup(capsys):
    assert app.main(["--lookup", "ambiguous"]) == 0
    out = capsys.readouterr().out
    assert '"ambiguous"' in out
    assert "All levels" in out


def test_lookup_estimated_word(capsys):
    assert app.main(["--lookup", "addictive"]) == 0
    assert "Estimated level" in capsys.readouterr().out

    assert app.main(["--lookup", "addictive", "--no-estimated"]) == 0
    assert "is not in the CEFR dictionary" in capsys.readouterr().out


def test_lookup_unknown_word(capsys):
    assert app.main(["--lookup", "qwzxv"]) == 0
    assert "is not in the CEFR dictionary" in capsys.readouterr().out


def test_no_inputs_shows_help(capsys):
    assert app.main([]) == 1
    assert "usage:" in capsys.readouterr().out


def test_no_supported_files(tmp_path, capsys):
    assert app.main([str(tmp_path)]) == 1
    assert "No files to scan" in capsys.readouterr().out


def test_min_level_above_max_level_is_rejected():
    with pytest.raises(SystemExit):
        app.main(["sample/", "--min-level", "C2", "--max-level", "B2"])
