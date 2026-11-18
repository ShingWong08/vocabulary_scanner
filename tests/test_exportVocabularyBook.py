import csv
import json

import openpyxl

from vocabulary_scanner.exportVocabularyBook import buildBookRows, exportVocabularyBook, loadBookCSV
from vocabulary_scanner.scanText import PHRASE_KIND, WORD_KIND, ScanResult, VocabularyEntry, scanText


def makeEntries():
    return [
        VocabularyEntry("scrutinize", "C1", ("C1",), ("verb",), WORD_KIND, 1, {"a.txt"}, "Bad\x0bchar.", "examine", "審查"),
        VocabularyEntry("ambiguous", "B2", ("B2", "C1"), ("adjective",), WORD_KIND, 3, {"a.txt", "b.txt"}, "Tab\there.", "", ""),
        VocabularyEntry("climate change", "B2", ("B2",), ("noun",), PHRASE_KIND, 1, {"a.txt"}, "", "", ""),
    ]


def test_rows_sorted_by_level_or_count():
    assert [row["word"] for row in buildBookRows(makeEntries())] == ["ambiguous", "climate change", "scrutinize"]
    assert [row["word"] for row in buildBookRows(makeEntries(), sortBy="count")] == ["ambiguous", "climate change", "scrutinize"]


def test_default_sort_is_level_then_alphabetical():
    entries = makeEntries() + [
        VocabularyEntry("according to", "B2", ("B2",), (), PHRASE_KIND, 9),
        VocabularyEntry("Zebra", "A1", ("A1",), (), WORD_KIND, 1),
        VocabularyEntry("apple", "A1", ("A1",), (), WORD_KIND, 1),
        VocabularyEntry("bridge", "B1", ("B1",), (), WORD_KIND, 1),
        VocabularyEntry("absurd", "C1", ("C1",), (), WORD_KIND, 1),
    ]

    words = [row["word"] for row in buildBookRows(entries)]

    # A1 -> A2 -> B1 -> B2 -> C1, alphabetical inside each level, words and phrases mixed
    assert words == ["apple", "Zebra", "bridge", "according to", "ambiguous", "climate change", "absurd", "scrutinize"]


def test_export_writes_every_file(dictionary, tmp_path):
    rows = buildBookRows(makeEntries())
    scanResult = scanText("The cat is ambiguous.", dictionary)

    paths = exportVocabularyBook(rows, scanResult, str(tmp_path / "out"))

    assert len(paths) == 6
    workbook = openpyxl.load_workbook(paths[0])
    sheet = workbook["單詞簿"]
    assert sheet.max_row == 4
    assert "\x0b" not in sheet["I4"].value  # control characters are removed for Excel
    assert workbook["等級統計"]["C2"].value == 1  # A1 count

    ankiLines = (tmp_path / "out" / "vocabulary_anki.tsv").read_text(encoding="utf-8-sig").splitlines()
    assert all(len(eachLine.split("\t")) == 6 for eachLine in ankiLines)

    eudicWords = (tmp_path / "out" / "vocabulary_eudic.txt").read_text(encoding="utf-8").split()
    assert eudicWords == ["ambiguous", "scrutinize"]


def test_csv_book_can_be_loaded_back(tmp_path):
    rows = buildBookRows(makeEntries())
    outputDir = tmp_path / "out"
    exportVocabularyBook(rows, ScanResult(), str(outputDir))

    entries = loadBookCSV(str(outputDir / "vocabulary_book.csv"))

    ambiguous = entries[("ambiguous", WORD_KIND)]
    assert ambiguous.count == 3
    assert ambiguous.sources == {"a.txt", "b.txt"}
    assert ambiguous.allLevels == ("B2", "C1")
    assert entries[("scrutinize", WORD_KIND)].translation == "審查"
    assert entries[("climate change", PHRASE_KIND)].kind == PHRASE_KIND


def test_estimated_levels_are_marked_in_every_file(tmp_path):
    entries = [VocabularyEntry("addictive", "B2", ("B2",), (), WORD_KIND, 1, {"a.txt"}, estimated=True)]
    outputDir = tmp_path / "out"
    exportVocabularyBook(buildBookRows(entries), ScanResult(), str(outputDir))

    sheet = openpyxl.load_workbook(outputDir / "vocabulary_book.xlsx")["單詞簿"]
    assert sheet["E1"].value == "推算等級"
    assert sheet["E2"].value == "推算"

    ankiFields = (outputDir / "vocabulary_anki.tsv").read_text(encoding="utf-8-sig").split("\t")
    assert ankiFields[3] == "B2*"

    report = (outputDir / "analysis_report.txt").read_text(encoding="utf-8")
    assert "addictive*" in report


def test_csv_has_no_estimated_column(tmp_path):
    entries = [VocabularyEntry("addictive", "B2", ("B2",), (), WORD_KIND, 1, {"a.txt"}, estimated=True)]
    outputDir = tmp_path / "out"
    exportVocabularyBook(buildBookRows(entries), ScanResult(), str(outputDir))

    with open(outputDir / "vocabulary_book.csv", encoding="utf-8-sig", newline="") as csvFile:
        reader = csv.DictReader(csvFile)
        assert "estimated" not in reader.fieldnames
        assert [row["word"] for row in reader] == ["addictive"]

    # JSON still says which levels are estimated
    book = json.loads((outputDir / "vocabulary_book.json").read_text(encoding="utf-8"))
    assert book["entries"][0]["estimated"] == "推算"


def test_old_book_without_estimated_column_loads(tmp_path):
    path = tmp_path / "old.csv"
    path.write_text("word,type,level,count\ncat,單詞,A1,2\n", encoding="utf-8-sig")
    assert loadBookCSV(str(path))[("cat", WORD_KIND)].estimated is False


def test_load_book_skips_bad_rows(tmp_path):
    path = tmp_path / "book.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as csvFile:
        writer = csv.DictWriter(csvFile, fieldnames=["word", "type", "level", "all_levels", "count"])
        writer.writeheader()
        writer.writerow({"word": "good", "type": "單詞", "level": "B2", "all_levels": "", "count": "x"})
        writer.writerow({"word": "", "type": "單詞", "level": "B2"})
        writer.writerow({"word": "bad", "type": "單詞", "level": "Z9"})

    entries = loadBookCSV(str(path))

    assert list(entries) == [("good", WORD_KIND)]
    assert entries[("good", WORD_KIND)].allLevels == ("B2",)
    assert entries[("good", WORD_KIND)].count == 0


def test_missing_book_loads_as_empty(tmp_path):
    assert loadBookCSV(str(tmp_path / "missing.csv")) == {}
