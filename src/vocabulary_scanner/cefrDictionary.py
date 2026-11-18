import csv
import os
import unicodedata
from collections import defaultdict
from typing import NamedTuple


LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_RANK = {eachLevel: index for index, eachLevel in enumerate(LEVEL_ORDER)}

LEVEL_NAMES = {
    "A1": "入門 Beginner",
    "A2": "初級 Elementary",
    "B1": "中級 Intermediate",
    "B2": "中高級 Upper-Intermediate",
    "C1": "高級 Advanced",
    "C2": "精通 Proficiency",
}

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DICTIONARY_PATH = os.path.join(PACKAGE_DIR, "data", "cefr_words.csv")
DEFAULT_ESTIMATED_PATH = os.path.join(PACKAGE_DIR, "data", "cefr_words_estimated.csv")

WORDNET_POS_TAGS = ["n", "v", "a", "r"]
ADVERB_SUFFIX = "ly"
MIN_ADVERB_LENGTH = 5


class DictionaryHit(NamedTuple):
    word: str
    level: str
    allLevels: tuple
    partsOfSpeech: tuple
    estimated: bool = False  # True when the level comes from the estimated dictionary


def normalize(text: str) -> str:

    """
    Lowercase the text and remove accents.
    Only letters, digits, spaces, hyphens and apostrophes are kept.
    Example: "Café-Owner's" -> "cafe-owner's"
    """

    text = unicodedata.normalize("NFKD", text)
    text = "".join(eachChar for eachChar in text if not unicodedata.combining(eachChar))
    text = text.lower()
    text = "".join(eachChar for eachChar in text if eachChar.isalnum() or eachChar in " '-")
    text = " ".join(text.split())
    return text.strip(" '-")


def sortLevels(levels) -> tuple:

    """
    Return the valid CEFR levels from easiest to hardest, without duplicates.
    """

    validLevels = {eachLevel for eachLevel in levels if eachLevel in LEVEL_RANK}
    return tuple(sorted(validLevels, key=LEVEL_RANK.get))


class CefrDictionary:

    """
    Load the CEFR word list (word, pos, level, type) and look up the level of words and phrases.
    When a word is listed at several levels, the lowest (easiest) level is its main level.

    Words that are not in the main dictionary can fall back to the estimated dictionary
    (levels computed by the Maximax67 dataset); those hits are marked with estimated=True.
    """

    def __init__(
        self,
        dictionaryPath: str = DEFAULT_DICTIONARY_PATH,
        estimatedPath: str | None = DEFAULT_ESTIMATED_PATH,
    ):

        """
        Parameters:
            Optional:
                - dictionaryPath (str): Path to the main CEFR dictionary CSV.
                - estimatedPath (str | None): Path to the estimated dictionary CSV. None turns the fallback off.
            Default:
                - dictionaryPath: the bundled data/cefr_words.csv
                - estimatedPath: the bundled data/cefr_words_estimated.csv (skipped if the file is missing)
        Raises:
            FileNotFoundError: If the main dictionary file does not exist.
        """

        self.words = defaultdict(lambda: {"levels": set(), "pos": set()})
        self.phrases = defaultdict(lambda: {"levels": set(), "pos": set()})
        self.wordAliases = {}  # "wellbeing" -> "well-being"
        self.estimatedWords = {}  # word -> level
        self.wordCache = {}

        if not os.path.exists(dictionaryPath):
            raise FileNotFoundError(f"CEFR dictionary not found: {dictionaryPath}")

        with open(dictionaryPath, encoding="utf-8", newline="") as dictionaryFile:
            for eachRow in csv.DictReader(dictionaryFile):
                self.addRow(eachRow)

        for eachWord in self.words:
            withoutHyphens = eachWord.replace("-", "")
            if withoutHyphens != eachWord and withoutHyphens not in self.words:
                self.wordAliases[withoutHyphens] = eachWord

        if estimatedPath is not None and os.path.exists(estimatedPath):
            self.loadEstimatedWords(estimatedPath)

    def loadEstimatedWords(self, estimatedPath: str) -> None:
        with open(estimatedPath, encoding="utf-8", newline="") as estimatedFile:
            for eachRow in csv.DictReader(estimatedFile):
                word = (eachRow.get("word") or "").strip()
                level = (eachRow.get("level") or "").strip().upper()

                if word != "" and level in LEVEL_RANK and word not in self.words:
                    self.estimatedWords[word] = level

    def addRow(self, row: dict) -> None:
        word = (row.get("word") or "").strip()
        level = (row.get("level") or "").strip().upper()
        partOfSpeech = (row.get("pos") or "").strip()
        kind = (row.get("type") or "word").strip()

        if word == "" or level not in LEVEL_RANK:
            return

        if kind == "phrase":
            bucket = self.phrases
        else:
            bucket = self.words

        bucket[word]["levels"].add(level)
        if partOfSpeech != "":
            bucket[word]["pos"].add(partOfSpeech)

    @staticmethod
    def makeHit(word: str, info: dict) -> DictionaryHit:
        allLevels = sortLevels(info["levels"])
        return DictionaryHit(word, allLevels[0], allLevels, tuple(sorted(info["pos"])))

    def lookupWord(self, token: str, lemmatizer=None) -> DictionaryHit | None:

        """
        Find the dictionary entry of a single word.
        The word is tried as written, without hyphens, and in its WordNet base forms (if a lemmatizer is given).
        The main dictionary is searched first; only when no spelling matches is the estimated dictionary used.
        Parameters:
            Mandatory:
                - token (str): The word as it appears in the text.
            Optional:
                - lemmatizer: An NLTK WordNetLemmatizer, used to turn "ran" into "run".
            Default:
                - lemmatizer: None
        Returns:
            DictionaryHit | None: None if the word is not in the dictionary.
        """

        cacheKey = (token, lemmatizer is not None)
        if cacheKey in self.wordCache:
            return self.wordCache[cacheKey]

        candidates = getTokenCandidates(token, lemmatizer)
        hit = self.findInMainDictionary(candidates)

        if hit is None:
            hit = self.findInEstimatedDictionary(candidates)

        self.wordCache[cacheKey] = hit
        return hit

    def findInMainDictionary(self, candidates: list[str]) -> DictionaryHit | None:
        for eachCandidate in candidates:
            word = self.wordAliases.get(eachCandidate, eachCandidate)
            if word in self.words:
                return self.makeHit(word, self.words[word])

        return None

    def findInEstimatedDictionary(self, candidates: list[str]) -> DictionaryHit | None:
        for eachCandidate in candidates:
            if eachCandidate in self.estimatedWords:
                level = self.estimatedWords[eachCandidate]
                return DictionaryHit(eachCandidate, level, (level,), (), estimated=True)

        return None

    def isEstimatedWord(self, word: str) -> bool:

        """
        Return True when the word's level comes from the estimated dictionary
        (it is not in the main CEFR-J / Octanove dictionary).
        """

        return word in self.estimatedWords and word not in self.words

    def lookupPhrase(self, phrase: str) -> DictionaryHit | None:

        """
        Find the dictionary entry of a phrase such as "climate change".
        Returns None if the phrase is not in the dictionary.
        """

        phrase = normalize(phrase)
        if phrase not in self.phrases:
            return None

        return self.makeHit(phrase, self.phrases[phrase])


def getTokenCandidates(token: str, lemmatizer=None) -> list[str]:

    """
    Spellings of a word to look up, in order, without duplicates:
    the normalized word, the word without hyphens, its WordNet base forms,
    and finally the word without "-ly" (WordNet does not turn "coherently" into "coherent").
    """

    base = normalize(token)
    candidates = []

    def addCandidate(spelling: str) -> None:
        if spelling != "" and spelling not in candidates:
            candidates.append(spelling)

    addCandidate(base)
    addCandidate(base.replace("-", ""))

    if lemmatizer is not None:
        for eachTag in WORDNET_POS_TAGS:
            try:
                lemma = lemmatizer.lemmatize(base, pos=eachTag)
            except Exception:
                continue

            addCandidate(lemma)
            addCandidate(lemma.replace("-", ""))

    if len(base) >= MIN_ADVERB_LENGTH and base.endswith(ADVERB_SUFFIX):
        addCandidate(base[: -len(ADVERB_SUFFIX)])

    return candidates


if __name__ == "__main__":
    dictionary = CefrDictionary()
    print(dictionary.lookupWord("ambiguous"))
    print(dictionary.lookupPhrase("according to"))
