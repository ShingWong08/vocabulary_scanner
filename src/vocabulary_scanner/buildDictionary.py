import argparse
import csv
import math
import os
import re

from vocabulary_scanner.cefrDictionary import (
    DEFAULT_DICTIONARY_PATH,
    DEFAULT_ESTIMATED_PATH,
    LEVEL_ORDER,
    LEVEL_RANK,
    normalize,
)
from vocabulary_scanner.chatColor import ChatColor


DEFAULT_SOURCES = [
    os.path.join("data", "cefrj-vocabulary-profile-1.6.csv"),
    os.path.join("data", "octanove-vocabulary-profile-c1c2-1.0.csv"),
]
DEFAULT_MAXIMAX_DIR = os.path.join("data", "maximax67")
MAXIMAX_FILES = ["words.csv", "word_pos.csv", "pos_tags.csv"]
MAXIMAX_DOWNLOAD_URL = "https://github.com/Maximax67/Words-CEFR-Dataset/tree/main/csv"

DICTIONARY_FIELDS = ["word", "pos", "level", "type"]
ESTIMATED_FIELDS = ["word", "level"]

# Penn Treebank tags left out of the estimated dictionary:
# cardinal numbers, foreign words, list markers, proper nouns, possessive endings and symbols
EXCLUDED_POS_TAGS = {"CD", "FW", "LS", "NNP", "NNPS", "POS", "SYM"}
ESTIMATED_WORD_PATTERN = re.compile(r"^[a-z]+(?:[-'][a-z]+)*$")
MIN_ESTIMATED_WORD_LENGTH = 3


def expandHeadword(headword: str) -> list[str]:

    """
    Split a headword with several spellings into normalized forms.
    Example: "agonize/agonise" -> ["agonize", "agonise"]
    """

    forms = []

    for eachForm in headword.split("/"):
        form = normalize(eachForm)
        if form != "" and form not in forms:
            forms.append(form)

    return forms


def buildDictionary(sourcePaths: list[str], outputPath: str = DEFAULT_DICTIONARY_PATH) -> list[dict]:

    """
    Combine the raw CEFR word lists into the main dictionary CSV used by the scanner.
    Parameters:
        Mandatory:
            - sourcePaths (list[str]): Raw CSV files with "headword", "pos" and "CEFR" columns
              (CEFR-J for A1-B2, Octanove for C1-C2; see data/SOURCES.md).
        Optional:
            - outputPath (str): Where to write the dictionary.
        Default:
            - outputPath: the bundled src/vocabulary_scanner/data/cefr_words.csv
    Returns:
        list[dict]: The rows that were written.
    """

    entries = set()

    for eachPath in sourcePaths:
        with open(eachPath, encoding="utf-8", newline="") as sourceFile:
            for eachRow in csv.DictReader(sourceFile):
                level = (eachRow.get("CEFR") or "").strip().upper()
                if level not in LEVEL_RANK:
                    continue

                partOfSpeech = (eachRow.get("pos") or "").strip().lower()

                for eachForm in expandHeadword(eachRow.get("headword") or ""):
                    kind = "phrase" if " " in eachForm else "word"
                    entries.add((eachForm, partOfSpeech, level, kind))

    rows = [dict(zip(DICTIONARY_FIELDS, eachEntry)) for eachEntry in entries]
    rows.sort(key=lambda row: (row["type"], row["word"], row["level"], row["pos"]))

    writeCSV(outputPath, DICTIONARY_FIELDS, rows)
    return rows


def isRealWordInWordNet(word: str) -> bool:

    """
    Return True when WordNet knows the word as an ordinary word, not only as a name.
    Example: "longevity" -> True, "woodward" (only a person's name) -> False
    """

    from nltk.corpus import wordnet

    synsets = wordnet.synsets(word)
    return any(len(eachSynset.instance_hypernyms()) == 0 for eachSynset in synsets)


def toCefrLevel(numericLevel: float) -> str:

    """
    Turn a Maximax67 level (1.0 = A1 ... 6.0 = C2) into a CEFR level, rounding to the nearest level.
    Example: 4.4 -> "B2", 4.5 -> "C1"
    """

    rank = math.floor(numericLevel + 0.5)
    rank = min(len(LEVEL_ORDER), max(1, rank))
    return LEVEL_ORDER[rank - 1]


def buildEstimatedDictionary(
    maximaxDir: str,
    mainWords: set,
    outputPath: str = DEFAULT_ESTIMATED_PATH,
    isRealWord=isRealWordInWordNet,
) -> list[dict]:

    """
    Build the estimated-level dictionary from the Maximax67 Words-CEFR-Dataset.
    Its levels are computed from CEFR-J plus word frequency, so they are only used for words
    that are not in the main dictionary.
    Parameters:
        Mandatory:
            - maximaxDir (str): Folder with words.csv, word_pos.csv and pos_tags.csv.
            - mainWords (set): Words of the main dictionary (these are left out).
        Optional:
            - outputPath (str): Where to write the estimated dictionary.
            - isRealWord (callable): Filter that removes names and junk words.
        Default:
            - outputPath: the bundled src/vocabulary_scanner/data/cefr_words_estimated.csv
            - isRealWord: isRealWordInWordNet
    Returns:
        list[dict]: The rows that were written ({"word", "level"}).
    """

    excludedTagIDs = set()
    with open(os.path.join(maximaxDir, "pos_tags.csv"), encoding="utf-8", newline="") as tagFile:
        for eachRow in csv.DictReader(tagFile):
            if eachRow["tag"] in EXCLUDED_POS_TAGS:
                excludedTagIDs.add(eachRow["tag_id"])

    wordsByID = {}
    with open(os.path.join(maximaxDir, "words.csv"), encoding="utf-8", newline="") as wordFile:
        for eachRow in csv.DictReader(wordFile):
            wordsByID[eachRow["word_id"]] = eachRow["word"]

    knownWords = set(mainWords) | {eachWord.replace("-", "") for eachWord in mainWords}
    lowestLevels = {}

    with open(os.path.join(maximaxDir, "word_pos.csv"), encoding="utf-8", newline="") as wordPosFile:
        for eachRow in csv.DictReader(wordPosFile):
            if eachRow["pos_tag_id"] in excludedTagIDs:
                continue

            word = normalize(wordsByID.get(eachRow["word_id"]) or "")
            if not isUsableEstimatedWord(word, knownWords):
                continue

            try:
                level = float(eachRow["level"])
            except ValueError:
                continue

            if word not in lowestLevels or level < lowestLevels[word]:
                lowestLevels[word] = level

    rows = []
    for eachWord in sorted(lowestLevels):
        if isRealWord(eachWord):
            rows.append({"word": eachWord, "level": toCefrLevel(lowestLevels[eachWord])})

    writeCSV(outputPath, ESTIMATED_FIELDS, rows)
    return rows


def isUsableEstimatedWord(word: str, knownWords: set) -> bool:
    if len(word) < MIN_ESTIMATED_WORD_LENGTH:
        return False

    if not ESTIMATED_WORD_PATTERN.match(word):
        return False

    return word not in knownWords and word.replace("-", "") not in knownWords


def writeCSV(outputPath: str, fieldNames: list[str], rows: list[dict]) -> None:
    outputFolder = os.path.dirname(outputPath)
    if outputFolder != "":
        os.makedirs(outputFolder, exist_ok=True)

    with open(outputPath, "w", encoding="utf-8", newline="") as outputFile:
        writer = csv.DictWriter(outputFile, fieldnames=fieldNames)
        writer.writeheader()
        writer.writerows(rows)


def main(arguments: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the CEFR dictionaries used by the scanner.")
    parser.add_argument("sources", nargs="*", default=DEFAULT_SOURCES, help="raw CEFR CSV files (default: CEFR-J 1.6 + Octanove in data/)")
    parser.add_argument("-o", "--output", default=DEFAULT_DICTIONARY_PATH, help="main dictionary CSV")
    parser.add_argument("--maximax-dir", default=DEFAULT_MAXIMAX_DIR, help="Maximax67 dataset folder (default: data/maximax67)")
    parser.add_argument("--estimated-output", default=DEFAULT_ESTIMATED_PATH, help="estimated dictionary CSV")
    parser.add_argument("--no-estimated", action="store_true", help="only build the main dictionary")
    options = parser.parse_args(arguments)

    rows = buildDictionary(options.sources, options.output)
    wordCount = len([eachRow for eachRow in rows if eachRow["type"] == "word"])
    phraseCount = len(rows) - wordCount
    print(ChatColor.paint(f"Wrote {options.output}: {wordCount} words, {phraseCount} phrases.", ChatColor.GREEN))

    if options.no_estimated:
        return

    missingFiles = [
        eachName for eachName in MAXIMAX_FILES
        if not os.path.exists(os.path.join(options.maximax_dir, eachName))
    ]
    if len(missingFiles) > 0:
        message = (
            f"Skipped the estimated dictionary: {', '.join(missingFiles)} not found in {options.maximax_dir}. "
            f"The existing {os.path.basename(options.estimated_output)} is kept. "
            f"To rebuild it, download those files from {MAXIMAX_DOWNLOAD_URL}"
        )
        print(ChatColor.paint(message, ChatColor.ORANGE))
        return

    mainWords = {eachRow["word"] for eachRow in rows if eachRow["type"] == "word"}
    print(ChatColor.paint("Building the estimated dictionary (this takes a minute)...", ChatColor.BLUE))
    estimatedRows = buildEstimatedDictionary(options.maximax_dir, mainWords, options.estimated_output)
    print(ChatColor.paint(f"Wrote {options.estimated_output}: {len(estimatedRows)} estimated words.", ChatColor.GREEN))


if __name__ == "__main__":
    main()
