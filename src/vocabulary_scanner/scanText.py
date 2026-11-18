import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from vocabulary_scanner.cefrDictionary import CefrDictionary, DictionaryHit, normalize, sortLevels


WORD_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[’'‐‑-][A-Za-zÀ-ÖØ-öø-ÿ]+)*")
PARAGRAPH_BREAK_PATTERN = re.compile(r"\n\s*\n+")
SENTENCE_END_PATTERN = re.compile(r"(?<=[.!?…])\s+")
LETTER_PATTERN = re.compile(r"[A-Za-z]")
# Web addresses, DOIs and e-mail addresses are not words ("https", "doi", "org"...)
LINK_PATTERN = re.compile(r"\b(?:https?://|www\.|doi:)\S+|\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)

MAX_EXAMPLE_LENGTH = 240
PHRASE_LENGTHS = [4, 3, 2]  # Longer phrases are matched first

WORD_KIND = "word"
PHRASE_KIND = "phrase"


@dataclass
class VocabularyEntry:

    """
    One word or phrase found in the scanned files.
    """

    word: str
    level: str
    allLevels: tuple
    partsOfSpeech: tuple
    kind: str  # WORD_KIND or PHRASE_KIND
    count: int = 0
    sources: set = field(default_factory=set)
    example: str = ""
    definition: str = ""
    translation: str = ""
    estimated: bool = False  # True when the level comes from the estimated dictionary

    @classmethod
    def fromHit(cls, hit: DictionaryHit, kind: str) -> "VocabularyEntry":
        return cls(hit.word, hit.level, hit.allLevels, hit.partsOfSpeech, kind, estimated=hit.estimated)

    def addOccurrence(self, sourceLabel: str, sentence: str) -> None:
        self.count += 1
        self.sources.add(sourceLabel)

        if self.example == "":
            self.example = sentence


@dataclass
class ScanResult:

    """
    Everything found in one or more scanned texts.
        - entries: {(word, kind): VocabularyEntry}
        - levelTokenCounts: how many times words of each level appeared
        - levelUniqueWords: the different words of each level
        - unknownWords: words that are not in the CEFR dictionary, with their counts
    """

    entries: dict = field(default_factory=dict)
    levelTokenCounts: Counter = field(default_factory=Counter)
    levelUniqueWords: defaultdict = field(default_factory=lambda: defaultdict(set))
    unknownWords: Counter = field(default_factory=Counter)

    @property
    def totalTokens(self) -> int:
        return sum(self.levelTokenCounts.values()) + sum(self.unknownWords.values())

    @property
    def totalUniqueWords(self) -> int:
        knownWords = sum(len(eachWords) for eachWords in self.levelUniqueWords.values())
        return knownWords + len(self.unknownWords)

    def merge(self, other: "ScanResult") -> None:

        """
        Add the results of another scan (e.g. the next file) to this one.
        """

        mergeEntries(self.entries, other.entries)
        self.levelTokenCounts.update(other.levelTokenCounts)
        self.unknownWords.update(other.unknownWords)

        for eachLevel, eachWords in other.levelUniqueWords.items():
            self.levelUniqueWords[eachLevel] |= eachWords


def splitSentences(text: str) -> list[str]:

    """
    Split text into sentences. Blank lines separate paragraphs, while single line breaks
    inside a paragraph are treated as spaces (so hard-wrapped lines do not cut sentences).
    Web addresses and e-mail addresses are removed first.
    Very long sentences are shortened to MAX_EXAMPLE_LENGTH characters.
    """

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = LINK_PATTERN.sub(" ", text)
    sentences = []

    for eachParagraph in PARAGRAPH_BREAK_PATTERN.split(text):
        paragraph = " ".join(eachParagraph.split())
        if paragraph == "":
            continue

        for eachSentence in SENTENCE_END_PATTERN.split(paragraph):
            sentence = eachSentence.strip()
            if sentence == "" or not LETTER_PATTERN.search(sentence):
                continue

            if len(sentence) > MAX_EXAMPLE_LENGTH:
                sentence = sentence[:MAX_EXAMPLE_LENGTH].rstrip() + "…"

            sentences.append(sentence)

    return sentences


def scanText(text: str, dictionary: CefrDictionary, lemmatizer=None, sourceLabel: str = "") -> ScanResult:

    """
    Find the CEFR level of every word and phrase in a text.
    Parameters:
        Mandatory:
            - text (str): The text to scan.
            - dictionary (CefrDictionary): The CEFR dictionary.
        Optional:
            - lemmatizer: An NLTK WordNetLemmatizer, so that "ran" is matched as "run".
            - sourceLabel (str): Name of the file the text comes from, saved with each entry.
        Default:
            - lemmatizer: None
            - sourceLabel: ""
    Returns:
        ScanResult: The words and phrases found, with level statistics.
    """

    result = ScanResult()

    for eachSentence in splitSentences(text):
        tokens = WORD_PATTERN.findall(eachSentence)
        scanWords(tokens, eachSentence, dictionary, lemmatizer, sourceLabel, result)
        scanPhrases(tokens, eachSentence, dictionary, sourceLabel, result)

    return result


def scanWords(tokens, sentence, dictionary, lemmatizer, sourceLabel, result: ScanResult) -> None:
    for eachToken in tokens:
        hit = dictionary.lookupWord(eachToken, lemmatizer)

        if hit is None:
            result.unknownWords[normalize(eachToken)] += 1
            continue

        result.levelTokenCounts[hit.level] += 1
        result.levelUniqueWords[hit.level].add(hit.word)

        entry = result.entries.setdefault((hit.word, WORD_KIND), VocabularyEntry.fromHit(hit, WORD_KIND))
        entry.addOccurrence(sourceLabel, sentence)


def scanPhrases(tokens, sentence, dictionary, sourceLabel, result: ScanResult) -> None:

    """
    Match phrases of 4, 3 and 2 words. Longer phrases go first, and a word that is already
    part of a matched phrase is not used again.
    """

    usedPositions = set()

    for eachLength in PHRASE_LENGTHS:
        for start in range(len(tokens) - eachLength + 1):
            positions = range(start, start + eachLength)
            if any(eachPosition in usedPositions for eachPosition in positions):
                continue

            hit = dictionary.lookupPhrase(" ".join(tokens[start : start + eachLength]))
            if hit is None:
                continue

            entry = result.entries.setdefault((hit.word, PHRASE_KIND), VocabularyEntry.fromHit(hit, PHRASE_KIND))
            entry.addOccurrence(sourceLabel, sentence)
            usedPositions.update(positions)


def mergeEntries(targetEntries: dict, newEntries: dict) -> dict:

    """
    Merge newEntries into targetEntries (both {(word, kind): VocabularyEntry}).
    Counts are added and sources combined; existing examples, definitions and translations are kept.
    Returns targetEntries.
    """

    for key, newEntry in newEntries.items():
        if key not in targetEntries:
            targetEntries[key] = newEntry
            continue

        target = targetEntries[key]
        target.count += newEntry.count
        target.sources |= newEntry.sources
        target.example = target.example or newEntry.example
        target.definition = target.definition or newEntry.definition
        target.translation = target.translation or newEntry.translation
        target.allLevels = sortLevels(set(target.allLevels) | set(newEntry.allLevels))
        target.estimated = target.estimated and newEntry.estimated

    return targetEntries


if __name__ == "__main__":
    sample = "Policymakers seldom concur on how to alleviate inequality.\nClimate change is a profound risk."
    scanResult = scanText(sample, CefrDictionary(), sourceLabel="example")

    for eachEntry in scanResult.entries.values():
        print(eachEntry.level, eachEntry.kind, eachEntry.word)
