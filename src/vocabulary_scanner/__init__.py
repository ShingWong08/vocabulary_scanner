"""Scan English documents, find the CEFR level (A1-C2) of every word, and export a vocabulary book."""

__version__ = "0.2.1"

import argparse
import os
import sys
from collections import Counter

from vocabulary_scanner import connectWordNet, extractText, translation, visionOCR
from vocabulary_scanner.cefrDictionary import (
    DEFAULT_DICTIONARY_PATH,
    DEFAULT_ESTIMATED_PATH,
    LEVEL_NAMES,
    LEVEL_ORDER,
    LEVEL_RANK,
    CefrDictionary,
)
from vocabulary_scanner.chatColor import ChatColor
from vocabulary_scanner.exportVocabularyBook import buildBookRows, exportVocabularyBook, loadBookCSV
from vocabulary_scanner.scanText import WORD_KIND, ScanResult, mergeEntries, scanText


EXIT_OK = 0
EXIT_ERROR = 1

USAGE_EXAMPLES = """
Supported files: PDF (.pdf), Word (.docx), Excel (.xlsx), images (.png/.jpg/.tiff, macOS OCR),
plain text (.txt/.csv/.md/.html)

Examples:
  vocab-scanner sample/
  vocab-scanner a.pdf b.docx --merge output/vocabulary_book.csv
  vocab-scanner sample/ --translate zh-TW
  vocab-scanner --lookup ambiguous
"""


def main(arguments: list[str] | None = None) -> int:

    """
    Run the command line tool.
    Parameters:
        Optional:
            - arguments (list[str] | None): Command line arguments. None reads them from sys.argv.
        Default:
            - arguments: None
    Returns:
        int: 0 on success, 1 on error.
    """

    parser = buildArgumentParser()
    options = parser.parse_args(arguments)

    if LEVEL_RANK[options.min_level] > LEVEL_RANK[options.max_level]:
        parser.error("--min-level must not be higher than --max-level")

    if options.lookup is None and len(options.inputs) == 0:
        parser.print_help()
        return EXIT_ERROR

    estimatedPath = None if options.no_estimated else DEFAULT_ESTIMATED_PATH

    try:
        dictionary = CefrDictionary(options.dictionary, estimatedPath)
    except FileNotFoundError as error:
        print(ChatColor.paint(str(error), ChatColor.RED))
        print(ChatColor.paint("Rebuild it with: python -m vocabulary_scanner.buildDictionary", ChatColor.DARK_GRAY))
        return EXIT_ERROR

    lemmatizer, wordnet = connectWordNet.loadWordNet()

    if options.lookup is not None:
        return lookupWord(options, dictionary, lemmatizer, wordnet)

    return scanFiles(options, dictionary, lemmatizer, wordnet)


def buildArgumentParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vocab-scanner",
        description="Scan English documents, find the CEFR level of every word, and export a vocabulary book.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=USAGE_EXAMPLES,
    )

    parser.add_argument("inputs", nargs="*", help="files or folders to scan (folders are scanned recursively)")
    parser.add_argument("--out-dir", default="output", help="output folder (default: output)")
    parser.add_argument("--dictionary", default=DEFAULT_DICTIONARY_PATH, help="CEFR dictionary CSV")
    parser.add_argument("--min-level", default="B2", choices=LEVEL_ORDER, help="lowest level in the book (default: B2)")
    parser.add_argument("--max-level", default="C2", choices=LEVEL_ORDER, help="highest level in the book (default: C2)")
    parser.add_argument("--top", type=int, default=30, help="unknown words listed in the report (default: 30)")
    parser.add_argument("--no-definitions", action="store_true", help="do not add WordNet English definitions")
    parser.add_argument(
        "--no-estimated", action="store_true",
        help="only use CEFR-J / Octanove levels; skip estimated levels for words they do not list",
    )
    parser.add_argument("--merge", help="merge into an existing vocabulary_book.csv (adds up counts and sources)")
    parser.add_argument("--sort", choices=["level", "count"], default="level", help="sort the book by level or count")
    parser.add_argument("--lookup", help="look up the CEFR level of one word, then exit")
    parser.add_argument(
        "--ocr", choices=extractText.OCR_MODES, default="auto",
        help="auto = OCR PDFs without a text layer, force = OCR every PDF, off = never (default: auto; macOS only)",
    )
    parser.add_argument("--ocr-dpi", type=int, default=200, help="PDF render resolution for OCR (default: 200)")
    parser.add_argument("--translate", help="translate the words into a language, e.g. zh-TW, zh-CN, ja, ko, es, fr")
    parser.add_argument(
        "--translator", choices=translation.TRANSLATOR_CHOICES, default="auto",
        help="translation service: auto = Google, then MyMemory if Google stops answering (default: auto)",
    )
    parser.add_argument(
        "--translation-cache", default=translation.DEFAULT_CACHE_DIR,
        help="folder for cached translations (default: translation_cache)",
    )

    return parser


def lookupWord(options, dictionary: CefrDictionary, lemmatizer, wordnet) -> int:

    """
    Print the CEFR level, parts of speech, definition and (optionally) translation of one word.
    """

    hit = dictionary.lookupWord(options.lookup, lemmatizer)

    if hit is None:
        print(ChatColor.paint(f'"{options.lookup}" is not in the CEFR dictionary.', ChatColor.ORANGE))
        return EXIT_OK

    title = ChatColor.paint(f'"{hit.word}"', ChatColor.BOLD, ChatColor.VIOLET)
    level = ChatColor.paint(f"{hit.level} ({LEVEL_NAMES[hit.level]})", ChatColor.BOLD, ChatColor.GREEN)
    print(f"{title}  {level}")

    if hit.estimated:
        print(ChatColor.paint("  Estimated level (not in CEFR-J / Octanove; computed by the Maximax67 dataset)", ChatColor.ORANGE))
    else:
        print(f"  All levels: {'/'.join(hit.allLevels)}    Part of speech: {'/'.join(hit.partsOfSpeech) or '-'}")

    definition = connectWordNet.lookupDefinition(wordnet, hit.word, hit.partsOfSpeech)
    if definition != "":
        print(f"  Definition: {ChatColor.paint(definition, ChatColor.AQUA)}")

    if options.translate:
        targetLanguage = translation.resolveLanguage(options.translate)
        translations = translation.translateWords(
            [hit.word], targetLanguage, cacheDir=options.translation_cache, translatorChoice=options.translator,
        )
        if hit.word in translations:
            print(f"  Translation ({targetLanguage}): {translations[hit.word]}")

    return EXIT_OK


def scanFiles(options, dictionary: CefrDictionary, lemmatizer, wordnet) -> int:

    """
    Scan the input files, build the vocabulary book and write every output file.
    """

    files = extractText.collectInputFiles(options.inputs)
    if len(files) == 0:
        print(ChatColor.paint("No files to scan. Give PDF / Word / Excel / text files or folders.", ChatColor.RED))
        return EXIT_ERROR

    printOCRStatus(options.ocr)
    print(ChatColor.paint(f"Scanning {len(files)} file(s)...", ChatColor.BOLD, ChatColor.CYAN))

    scanResult = ScanResult()

    for eachFile in files:
        sourceLabel = getSourceLabel(eachFile)
        print(ChatColor.paint("  Scanning: ", ChatColor.DARK_GRAY) + sourceLabel)

        text = extractText.extractText(eachFile, ocrMode=options.ocr, ocrDPI=options.ocr_dpi)
        if text.strip() == "":
            print(ChatColor.paint(f"  No text found, skipped: {sourceLabel}", ChatColor.ORANGE))
            continue

        scanResult.merge(scanText(text, dictionary, lemmatizer, sourceLabel))

    minRank = LEVEL_RANK[options.min_level]
    maxRank = LEVEL_RANK[options.max_level]
    selectedEntries = {
        eachKey: eachEntry
        for eachKey, eachEntry in scanResult.entries.items()
        if minRank <= LEVEL_RANK[eachEntry.level] <= maxRank
    }

    if not options.no_definitions and wordnet is not None:
        print(ChatColor.paint("Looking up English definitions (WordNet)...", ChatColor.BLUE))
        addDefinitions(selectedEntries.values(), wordnet)

    if options.merge:
        existingEntries = loadBookCSV(options.merge)
        markEstimatedEntries(existingEntries.values(), dictionary)
        selectedEntries = mergeEntries(existingEntries, selectedEntries)
        print(ChatColor.paint(f"Merged into the existing book: {options.merge}", ChatColor.BLUE))

    if options.translate:
        addTranslations(selectedEntries.values(), options.translate, options.translation_cache, options.translator)

    rows = buildBookRows(selectedEntries.values(), sortBy=options.sort)
    outputPaths = exportVocabularyBook(rows, scanResult, options.out_dir, topUnknown=options.top)

    print(ChatColor.paint("\nOutput files:", ChatColor.BOLD))
    for eachPath in outputPaths:
        print(ChatColor.paint("  - ", ChatColor.DARK_GRAY) + eachPath)

    printSummary(rows, scanResult, options.min_level, options.max_level)
    return EXIT_OK


def printOCRStatus(ocrMode: str) -> None:
    if ocrMode == "off":
        return

    if visionOCR.isOCRAvailable():
        print(ChatColor.paint(f"OCR is on (mode: {ocrMode}).", ChatColor.DARK_GRAY))
    else:
        print(ChatColor.paint("OCR is not available (macOS only): scanned PDFs and images are skipped.", ChatColor.DARK_GRAY))


def getSourceLabel(filePath: str) -> str:

    """
    A short name for a file: its path relative to the current folder.
    On Windows a file on another drive has no relative path, so the full path is used.
    """

    try:
        return os.path.relpath(filePath)
    except ValueError:
        return os.path.abspath(filePath)


def markEstimatedEntries(entries, dictionary: CefrDictionary) -> None:

    """
    The CSV book does not store which levels are estimated, so check each loaded word against the dictionary.
    """

    for eachEntry in entries:
        eachEntry.estimated = eachEntry.kind == WORD_KIND and dictionary.isEstimatedWord(eachEntry.word)


def addDefinitions(entries, wordnet) -> None:
    for eachEntry in entries:
        if eachEntry.kind == WORD_KIND and eachEntry.definition == "":
            eachEntry.definition = connectWordNet.lookupDefinition(wordnet, eachEntry.word, eachEntry.partsOfSpeech)


def addTranslations(entries, language: str, cacheDir: str, translatorChoice: str = "auto") -> None:

    """
    Translate the word of every entry that has no translation yet.
    """

    entries = list(entries)
    targetLanguage = translation.resolveLanguage(language)
    words = sorted({eachEntry.word for eachEntry in entries if eachEntry.translation == ""})

    message = f"Translating {len(words)} word(s) into {targetLanguage} (cached in {cacheDir})..."
    print(ChatColor.paint(message, ChatColor.BLUE))

    translations = translation.translateWords(words, targetLanguage, cacheDir=cacheDir, translatorChoice=translatorChoice)

    for eachEntry in entries:
        if eachEntry.translation == "":
            eachEntry.translation = translations.get(eachEntry.word, "")

    missingCount = len([eachWord for eachWord in words if eachWord not in translations])
    if missingCount > 0:
        warning = f"{missingCount} word(s) could not be translated. Check your network and run again to retry."
        print(ChatColor.paint(warning, ChatColor.ORANGE))


def printSummary(rows: list[dict], scanResult: ScanResult, minLevel: str, maxLevel: str) -> None:
    line = ChatColor.paint("-" * 60, ChatColor.DARK_GRAY)
    totalTokens = scanResult.totalTokens

    print("\n" + ChatColor.paint("Scan complete", ChatColor.BOLD, ChatColor.GREEN))
    print(line)
    print(f"Total words: {totalTokens:,}    Different words: {scanResult.totalUniqueWords:,}")
    print(line)

    for eachLevel in LEVEL_ORDER:
        tokenCount = scanResult.levelTokenCounts.get(eachLevel, 0)
        uniqueCount = len(scanResult.levelUniqueWords.get(eachLevel, set()))
        if tokenCount == 0:
            continue

        percentage = tokenCount / totalTokens * 100
        print(f"  {eachLevel}  {tokenCount:>7,} times ({percentage:>5.1f}%)   {uniqueCount:>5} different words")

    unknownCount = sum(scanResult.unknownWords.values())
    print(f"  ??  {unknownCount:>7,} times            {len(scanResult.unknownWords):>5} not in the dictionary")
    print(line)

    levelCounts = Counter(eachRow["level"] for eachRow in rows)
    bookLevels = LEVEL_ORDER[LEVEL_RANK[minLevel] : LEVEL_RANK[maxLevel] + 1]
    perLevel = ", ".join(f"{eachLevel} {levelCounts.get(eachLevel, 0)}" for eachLevel in bookLevels)
    print(ChatColor.paint(f"Vocabulary book: {len(rows)} entries ({perLevel})", ChatColor.BOLD, ChatColor.GREEN))

    estimatedCount = len([eachRow for eachRow in rows if eachRow["estimated"]])
    if estimatedCount > 0:
        note = f"{estimatedCount} of them have estimated levels (marked 推算 in Excel, * in Anki and the report)."
        print(ChatColor.paint(note, ChatColor.DARK_GRAY))


if __name__ == "__main__":
    sys.exit(main())
