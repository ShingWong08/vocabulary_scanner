import csv
import json
import os
from datetime import datetime

from vocabulary_scanner.cefrDictionary import LEVEL_NAMES, LEVEL_ORDER, LEVEL_RANK, sortLevels
from vocabulary_scanner.scanText import PHRASE_KIND, WORD_KIND, ScanResult, VocabularyEntry


# These values are written into the CSV and read back by --merge, so they must not change
TYPE_NAMES = {WORD_KIND: "單詞", PHRASE_KIND: "片語"}

CSV_FIELDS = [
    "word", "translation", "type", "level", "pos", "pos_short", "all_levels",
    "count", "sources", "definition", "example",
]

# Written in the Excel "推算等級" column (the CSV has no such column;
# when merging, estimated levels are looked up in the dictionary again)
ESTIMATED_MARK = "推算"
# Added after the level in the Anki file and the report, e.g. "C2*"
ESTIMATED_LEVEL_SUFFIX = "*"

OUTPUT_FILES = {
    "excel": "vocabulary_book.xlsx",
    "csv": "vocabulary_book.csv",
    "anki": "vocabulary_anki.tsv",
    "eudic": "vocabulary_eudic.txt",
    "json": "vocabulary_book.json",
    "report": "analysis_report.txt",
}

EXCEL_HEADERS = ["單詞/片語", "翻譯", "類型", "等級(CEFR)", "推算等級", "詞性", "出現次數", "來源檔案", "英文定義", "例句"]
EXCEL_COLUMNS = ["word", "translation", "type", "level", "estimated", "pos_short", "count", "sources", "definition", "example"]
EXCEL_COLUMN_WIDTHS = [22, 20, 8, 10, 9, 12, 9, 26, 48, 48]
STATS_HEADERS = ["等級", "說明", "總出現次數", "不同單詞數"]
STATS_COLUMN_WIDTHS = [10, 30, 14, 14]

POS_ABBREVIATIONS = {
    "noun": "n.", "verb": "v.", "adjective": "adj.",
    "adverb": "adv.", "preposition": "prep.", "determiner": "det.",
    "pronoun": "pron.", "conjunction": "conj.", "interjection": "interj.",
    "number": "num.", "numeral": "num.", "phrasal verb": "phr. v.",
    "auxiliary verb": "aux.", "modal verb": "mod.", "modal auxiliary": "mod.",
    "be-verb": "be v.", "do-verb": "do v.", "have-verb": "have v.",
    "infinitive-to": "to-inf.", "vern": "v.",
}

SOURCE_SEPARATOR = "; "
LIST_SEPARATOR = "/"
REPORT_LINE = "-" * 52


def shortenPartsOfSpeech(partsOfSpeech: tuple) -> str:

    """
    Example: ("adjective", "noun") -> "adj./n."
    """

    return LIST_SEPARATOR.join(POS_ABBREVIATIONS.get(eachPart, eachPart) for eachPart in partsOfSpeech)


def buildBookRows(entries, sortBy: str = "level") -> list[dict]:

    """
    Turn VocabularyEntry objects into rows (dicts with the CSV_FIELDS keys) for exporting.
    Parameters:
        Mandatory:
            - entries: The VocabularyEntry objects to export.
        Optional:
            - sortBy (str): "level" = by level (A1, A2, B1, B2, C1, C2), then alphabetically;
                            "count" = most frequent first, then by level and alphabetically.
        Default:
            - sortBy: "level"
    Words and phrases are sorted together, so "according to" comes before "ambiguous".
    """

    rows = []

    for eachEntry in entries:
        rows.append({
            "word": eachEntry.word,
            "translation": eachEntry.translation,
            "type": TYPE_NAMES[eachEntry.kind],
            "level": eachEntry.level,
            "pos": LIST_SEPARATOR.join(eachEntry.partsOfSpeech),
            "pos_short": shortenPartsOfSpeech(eachEntry.partsOfSpeech),
            "all_levels": LIST_SEPARATOR.join(eachEntry.allLevels),
            "count": eachEntry.count,
            "sources": SOURCE_SEPARATOR.join(sorted(eachEntry.sources)),
            "definition": eachEntry.definition,
            "example": eachEntry.example,
            "estimated": ESTIMATED_MARK if eachEntry.estimated else "",
        })

    if sortBy == "count":
        rows.sort(key=lambda row: (-row["count"], *getLevelAlphabeticalKey(row)))
    else:
        rows.sort(key=getLevelAlphabeticalKey)

    return rows


def getLevelAlphabeticalKey(row: dict) -> tuple:

    """
    Sort key: level first (A1 -> C2), then the word in alphabetical order (ignoring case).
    """

    return (LEVEL_RANK[row["level"]], row["word"].casefold(), row["word"], row["type"])


def exportVocabularyBook(rows: list[dict], scanResult: ScanResult, outputDir: str, topUnknown: int = 30) -> list[str]:

    """
    Write the vocabulary book in every format (Excel, CSV, Anki, Eudic, JSON and a text report).
    Parameters:
        Mandatory:
            - rows (list[dict]): Rows from buildBookRows.
            - scanResult (ScanResult): The scan statistics, used by the Excel stats sheet and the report.
            - outputDir (str): Folder to write the files to (created if needed).
        Optional:
            - topUnknown (int): How many of the most common unknown words to list in the report.
        Default:
            - topUnknown: 30
    Returns:
        list[str]: Paths of the written files.
    """

    os.makedirs(outputDir, exist_ok=True)
    paths = {eachKey: os.path.join(outputDir, eachName) for eachKey, eachName in OUTPUT_FILES.items()}

    writeExcelBook(rows, scanResult, paths["excel"])
    writeCSVBook(rows, paths["csv"])
    writeAnkiTSV(rows, paths["anki"])
    writeEudicTXT(rows, paths["eudic"])
    writeJSONBook(rows, paths["json"])
    writeReport(rows, scanResult, paths["report"], topUnknown)

    return list(paths.values())


def writeCSVBook(rows: list[dict], filePath: str) -> None:

    """
    Write the CSV_FIELDS columns of every row; other keys (e.g. "estimated") are left out.
    """

    with open(filePath, "w", encoding="utf-8-sig", newline="") as csvFile:
        writer = csv.DictWriter(csvFile, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def cleanForExcel(value):

    """
    Remove control characters (often found in PDF text) that Excel files cannot store.
    """

    if not isinstance(value, str):
        return value

    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

    return ILLEGAL_CHARACTERS_RE.sub("", value)


def writeExcelBook(rows: list[dict], scanResult: ScanResult, filePath: str) -> None:

    """
    Write the vocabulary book sheet and a level statistics sheet to an Excel file.
    """

    import openpyxl
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    workbook = openpyxl.Workbook()

    bookSheet = workbook.active
    bookSheet.title = "單詞簿"
    bookSheet.append(EXCEL_HEADERS)

    for eachRow in rows:
        bookSheet.append([cleanForExcel(eachRow[eachColumn]) for eachColumn in EXCEL_COLUMNS])

    statsSheet = workbook.create_sheet("等級統計")
    statsSheet.append(STATS_HEADERS)

    for eachLevel in LEVEL_ORDER:
        tokenCount = scanResult.levelTokenCounts.get(eachLevel, 0)
        uniqueCount = len(scanResult.levelUniqueWords.get(eachLevel, set()))
        statsSheet.append([eachLevel, LEVEL_NAMES[eachLevel], tokenCount, uniqueCount])

    unknownCount = sum(scanResult.unknownWords.values())
    statsSheet.append(["未知", "不在字典中", unknownCount, len(scanResult.unknownWords)])
    statsSheet.append(["總計", "", scanResult.totalTokens, scanResult.totalUniqueWords])

    for eachSheet, eachWidths in [(bookSheet, EXCEL_COLUMN_WIDTHS), (statsSheet, STATS_COLUMN_WIDTHS)]:
        for eachCell in eachSheet[1]:
            eachCell.font = Font(bold=True)

        for columnNumber, eachWidth in enumerate(eachWidths, start=1):
            eachSheet.column_dimensions[get_column_letter(columnNumber)].width = eachWidth

    bookSheet.freeze_panes = "A2"
    workbook.save(filePath)


def getLevelLabel(row: dict) -> str:

    """
    The level with a "*" when it is estimated. Example: "C2*"
    """

    if row.get("estimated"):
        return row["level"] + ESTIMATED_LEVEL_SUFFIX

    return row["level"]


def writeAnkiTSV(rows: list[dict], filePath: str) -> None:

    """
    Write an Anki import file. Columns: word, definition, example, level, part of speech, translation.
    Estimated levels end with "*". Tabs and line breaks inside a field are replaced by spaces.
    """

    with open(filePath, "w", encoding="utf-8-sig", newline="") as tsvFile:
        for eachRow in rows:
            values = [
                eachRow["word"], eachRow["definition"], eachRow["example"],
                getLevelLabel(eachRow), eachRow["pos_short"], eachRow["translation"],
            ]
            fields = [" ".join(str(eachValue or "").split()) for eachValue in values]
            tsvFile.write("\t".join(fields) + "\n")


def writeEudicTXT(rows: list[dict], filePath: str) -> None:

    """
    Write a word list for Eudic, Youdao and similar apps: one single word per line (no phrases), easiest level first.
    """

    words = [eachRow for eachRow in rows if eachRow["type"] == TYPE_NAMES[WORD_KIND]]
    words.sort(key=getLevelAlphabeticalKey)

    with open(filePath, "w", encoding="utf-8", newline="") as textFile:
        for eachRow in words:
            textFile.write(eachRow["word"] + "\n")


def writeJSONBook(rows: list[dict], filePath: str) -> None:
    payload = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_entries": len(rows),
        },
        "entries": rows,
    }

    with open(filePath, "w", encoding="utf-8") as jsonFile:
        json.dump(payload, jsonFile, ensure_ascii=False, indent=2)


def writeReport(rows: list[dict], scanResult: ScanResult, filePath: str, topUnknown: int = 30) -> None:

    """
    Write a readable text report: level statistics, the vocabulary book, and the most common unknown words.
    """

    totalTokens = scanResult.totalTokens
    lines = [
        "英文文件 CEFR 單詞等級分析報告",
        "=" * 52,
        f"產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"總單詞數：{totalTokens:,}",
        f"不同單詞數：{scanResult.totalUniqueWords:,}",
        "",
        "各等級統計：",
        REPORT_LINE,
    ]

    for eachLevel in LEVEL_ORDER:
        tokenCount = scanResult.levelTokenCounts.get(eachLevel, 0)
        uniqueCount = len(scanResult.levelUniqueWords.get(eachLevel, set()))
        percentage = getPercentage(tokenCount, totalTokens)
        lines.append(
            f"{eachLevel} ({LEVEL_NAMES[eachLevel]}): 出現 {tokenCount:,} 次 ({percentage:.1f}%)，不同單詞 {uniqueCount}"
        )

    unknownCount = sum(scanResult.unknownWords.values())
    lines.append(f"未知: {unknownCount:,} 次（{len(scanResult.unknownWords)} 個不同單詞）")
    lines += ["", "單詞簿：", REPORT_LINE]

    if any(eachRow["estimated"] for eachRow in rows):
        lines.append(f"（標 {ESTIMATED_LEVEL_SUFFIX} 的單詞不在 CEFR-J / Octanove 字典中，等級由 Maximax67 資料集推算，僅供參考）")

    currentLevel = None
    for eachRow in rows:
        if eachRow["level"] != currentLevel:
            currentLevel = eachRow["level"]
            lines += ["", f"[{currentLevel}] {LEVEL_NAMES[currentLevel]}："]

        translation = f"【{eachRow['translation']}】" if eachRow["translation"] else ""
        definition = f" — {eachRow['definition']}" if eachRow["definition"] else ""
        partOfSpeech = eachRow["pos_short"] or "無詞性"
        mark = ESTIMATED_LEVEL_SUFFIX if eachRow["estimated"] else ""
        lines.append(f"  {eachRow['word']}{mark}{translation} ({partOfSpeech}) x{eachRow['count']}{definition}")

    mostCommonUnknown = scanResult.unknownWords.most_common(topUnknown)
    if len(mostCommonUnknown) > 0:
        lines += ["", "最常出現的未知單詞：", REPORT_LINE]
        for eachWord, eachCount in mostCommonUnknown:
            lines.append(f"  {eachWord}: {eachCount} 次")

    with open(filePath, "w", encoding="utf-8") as reportFile:
        reportFile.write("\n".join(lines) + "\n")


def getPercentage(part: int, total: int) -> float:
    if total == 0:
        return 0.0

    return part / total * 100


def loadBookCSV(filePath: str) -> dict:

    """
    Load a vocabulary_book.csv written earlier, so new results can be merged into it.
    Rows without a word or with an unknown level are skipped.
    Returns:
        dict: {(word, kind): VocabularyEntry}, or {} if the file does not exist.
    """

    entries = {}
    if not os.path.exists(filePath):
        return entries

    with open(filePath, encoding="utf-8-sig", newline="") as csvFile:
        for eachRow in csv.DictReader(csvFile):
            entry = rowToEntry(eachRow)
            if entry is not None:
                entries[(entry.word, entry.kind)] = entry

    return entries


def rowToEntry(row: dict) -> VocabularyEntry | None:
    word = (row.get("word") or "").strip()
    level = (row.get("level") or "").strip().upper()

    if word == "" or level not in LEVEL_RANK:
        return None

    if row.get("type") == TYPE_NAMES[PHRASE_KIND]:
        kind = PHRASE_KIND
    else:
        kind = WORD_KIND

    allLevels = sortLevels((row.get("all_levels") or "").split(LIST_SEPARATOR) + [level])
    partsOfSpeech = tuple(filter(None, (row.get("pos") or "").split(LIST_SEPARATOR)))
    sources = set(filter(None, (row.get("sources") or "").split(SOURCE_SEPARATOR)))

    try:
        count = int(row.get("count") or 0)
    except ValueError:
        count = 0

    return VocabularyEntry(
        word=word,
        level=level,
        allLevels=allLevels,
        partsOfSpeech=partsOfSpeech,
        kind=kind,
        count=count,
        sources=sources,
        example=row.get("example") or "",
        definition=row.get("definition") or "",
        translation=row.get("translation") or "",
    )
