from vocabulary_scanner.chatColor import ChatColor


WORDNET_PACKAGES = ["wordnet", "omw-1.4"]

POS_TO_WORDNET = {"noun": "n", "verb": "v", "adjective": "a", "adverb": "r"}
WORDNET_ADJECTIVE_TAGS = {"a", "s"}


def loadWordNet(downloadIfMissing: bool = True) -> tuple:

    """
    Load NLTK WordNet for lemmatization ("ran" -> "run") and English definitions.
    Parameters:
        Optional:
            - downloadIfMissing (bool): Download the WordNet data when it is not installed yet.
        Default:
            - downloadIfMissing: True
    Returns:
        tuple: (lemmatizer, wordnet), or (None, None) if NLTK or the WordNet data is not available.
        The scanner still works without them, but it cannot lemmatize or show definitions.
    """

    try:
        import nltk
        from nltk.corpus import wordnet
        from nltk.stem import WordNetLemmatizer
    except ImportError:
        print(ChatColor.paint("nltk is not installed. Lemmatization and definitions are skipped.", ChatColor.ORANGE))
        return None, None

    if not isWordNetReady(wordnet):
        if downloadIfMissing:
            print(ChatColor.paint("Downloading WordNet data (first run only)...", ChatColor.BLUE))
            for eachPackage in WORDNET_PACKAGES:
                try:
                    nltk.download(eachPackage, quiet=True)
                except Exception:
                    pass

        if not isWordNetReady(wordnet):
            warning = "WordNet data is not available. Lemmatization and definitions are skipped."
            print(ChatColor.paint(warning, ChatColor.ORANGE))
            return None, None

    return WordNetLemmatizer(), wordnet


def isWordNetReady(wordnet) -> bool:
    try:
        wordnet.synsets("test")
    except Exception:
        return False

    return True


def lookupDefinition(wordnet, word: str, partsOfSpeech: tuple = ()) -> str:

    """
    Return the first WordNet definition of a word, or "" if there is none.
    Parameters:
        Mandatory:
            - wordnet: The NLTK WordNet corpus from loadWordNet (None returns "").
            - word (str): The word to define.
        Optional:
            - partsOfSpeech (tuple): Preferred parts of speech, e.g. ("noun", "verb").
              Definitions with a matching part of speech are chosen first.
        Default:
            - partsOfSpeech: ()
    """

    if wordnet is None:
        return ""

    synsets = wordnet.synsets(word)
    if len(synsets) == 0 and "-" in word:
        synsets = wordnet.synsets(word.replace("-", ""))

    if len(synsets) == 0:
        return ""

    wantedTags = set()
    for eachPartOfSpeech in partsOfSpeech:
        if eachPartOfSpeech in POS_TO_WORDNET:
            wantedTags.add(POS_TO_WORDNET[eachPartOfSpeech])

    if "a" in wantedTags:
        wantedTags |= WORDNET_ADJECTIVE_TAGS

    matchingSynsets = [eachSynset for eachSynset in synsets if eachSynset.pos() in wantedTags]
    if len(matchingSynsets) > 0:
        synsets = matchingSynsets

    return synsets[0].definition()


if __name__ == "__main__":
    lemmatizer, wordnet = loadWordNet()
    print(lookupDefinition(wordnet, "ambiguous", ("adjective",)))
