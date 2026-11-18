import re

import requests


MYMEMORY_URL = "https://api.mymemory.translated.net/get"
HTTP_TOO_MANY_REQUESTS = 429
LIMIT_STATUS_CODES = {403, 429}
WARNING_PREFIX = "MYMEMORY WARNING"

# MyMemory's own machine translation. Its other matches come from translation memories
# (e.g. software interface strings), which are often wrong for single words.
MACHINE_TRANSLATION_AUTHOR = "MT!"

MARKUP_PATTERN = re.compile(r"<[^>]+>")                     # <g>次級</g>
PLACEHOLDER_PATTERN = re.compile(r"\(\$[^)]*\)|\{[^}]*\}")  # ($Diagnostic), {0}
ACCELERATOR_PATTERN = re.compile(r"&(?=\w)")                # &診斷
EDGE_CHARACTERS = " \t\r\n.,;:!?。，；：！？、…\"'“”‘’()（）[]［］【】「」『』*-–—/"
LETTER_PATTERN = re.compile(r"[^\W\d_]")


class MyMemoryLimitError(Exception):

    """
    MyMemory refused the request because the free daily limit was reached (too many requests).
    """


def translateWithMyMemory(
    word: str,
    targetLanguage: str,
    sourceLanguage: str = "en",
    myMemoryURL: str = MYMEMORY_URL,
    timeout: float = 15,
) -> str:

    """
    Translate one word with the free MyMemory API (no API key needed).
    Parameters:
        Mandatory:
            - word (str): The word to translate.
            - targetLanguage (str): Target language code, e.g. "zh-TW".
        Optional:
            - sourceLanguage (str): Source language code.
            - myMemoryURL (str): The MyMemory API URL.
            - timeout (float): Request timeout in seconds.
        Default:
            - sourceLanguage: "en"
            - myMemoryURL: "https://api.mymemory.translated.net/get"
            - timeout: 15
    Returns:
        str: The translation, or "" if MyMemory has none (it answers with the word itself).
        MyMemory's machine translation is preferred over its translation-memory matches,
        and markup such as "<g>" or "($Name)" is removed.
    Raises:
        MyMemoryLimitError: When the free daily limit is used up.
        requests.RequestException: On network or server errors.
    """

    word = word.strip()
    if word == "":
        raise ValueError("Word cannot be empty.")

    parameters = {"q": word, "langpair": f"{sourceLanguage}|{targetLanguage}"}
    response = requests.get(myMemoryURL, params=parameters, timeout=timeout)

    if response.status_code == HTTP_TOO_MANY_REQUESTS:
        raise MyMemoryLimitError("MyMemory: too many requests")

    response.raise_for_status()
    data = response.json()

    topTranslation = ((data.get("responseData") or {}).get("translatedText") or "").strip()

    if isLimitResponse(data, topTranslation):
        raise MyMemoryLimitError("MyMemory: too many requests (free daily limit reached)")

    return chooseTranslation(word, topTranslation, data.get("matches") or [])


def chooseTranslation(word: str, topTranslation: str, matches: list) -> str:

    """
    Pick the best translation, in this order:
        1. MyMemory's machine translation ("MT!")
        2. a translation-memory match for exactly this word
        3. MyMemory's top answer
    The first one that is still usable after cleanTranslation wins. Returns "" if none is usable.
    """

    machineTranslations = []
    exactMatches = []

    for eachMatch in matches:
        if not isinstance(eachMatch, dict):
            continue

        if eachMatch.get("created-by") == MACHINE_TRANSLATION_AUTHOR:
            machineTranslations.append(eachMatch.get("translation") or "")
        elif cleanTranslation(eachMatch.get("segment") or "").lower() == word.lower():
            exactMatches.append(eachMatch.get("translation") or "")

    for eachCandidate in machineTranslations + exactMatches + [topTranslation]:
        translation = cleanTranslation(eachCandidate)

        if translation != "" and translation.lower() != word.lower():
            return translation

    return ""


def cleanTranslation(text: str) -> str:

    """
    Remove markup left over from software translations and trim punctuation at both ends.
    Returns "" when nothing but digits or symbols is left.
    Example: "<g>次級</g>" -> "次級", "&診斷測試($Diagnostic)" -> "診斷測試", "［預防］:" -> "預防"
    """

    text = MARKUP_PATTERN.sub("", text)
    text = PLACEHOLDER_PATTERN.sub("", text)
    text = ACCELERATOR_PATTERN.sub("", text)
    text = " ".join(text.split()).strip(EDGE_CHARACTERS)

    if not LETTER_PATTERN.search(text):
        return ""

    return text


def isLimitResponse(data: dict, translation: str) -> bool:

    """
    MyMemory sometimes answers HTTP 200 but puts a limit warning in the translation, so check both.
    """

    if data.get("quotaFinished"):
        return True

    if data.get("responseStatus") in LIMIT_STATUS_CODES:
        return True

    return translation.upper().startswith(WARNING_PREFIX)


if __name__ == "__main__":
    print(translateWithMyMemory("ambiguous", "zh-TW"))
