import json
import os
import time

from vocabulary_scanner import connectGoogleTranslate, connectMyMemory
from vocabulary_scanner.chatColor import ChatColor


DEFAULT_CACHE_DIR = "translation_cache"

TRANSLATOR_CHOICES = ["auto", "google", "mymemory"]
# "auto" tries Google first and switches to MyMemory when Google stops answering
TRANSLATOR_ORDER = {
    "auto": ["google", "mymemory"],
    "google": ["google"],
    "mymemory": ["mymemory"],
}
TRANSLATOR_NAMES = {"google": "Google Translate", "mymemory": "MyMemory"}

# Google allows about 5 requests per second, so wait a little between words
DELAY_BETWEEN_WORDS = 0.25
# When a service says "too many requests", wait 1s, 2s, 4s before giving up on it
MAX_RETRIES = 3
FIRST_RETRY_DELAY = 1.0
# Stop using a service after this many words in a row fail with other errors (e.g. no network)
MAX_CONSECUTIVE_FAILURES = 3

RATE_LIMIT_ERROR_NAMES = {"TooManyRequests", "MyMemoryLimitError"}

LANGUAGE_ALIASES = {
    # Traditional Chinese
    "中文": "zh-TW", "繁體中文": "zh-TW", "繁體": "zh-TW", "繁中": "zh-TW",
    "zh": "zh-TW", "zh-tw": "zh-TW", "zh-hant": "zh-TW", "zh-hk": "zh-TW", "zh-mo": "zh-TW",
    # Simplified Chinese
    "簡體中文": "zh-CN", "簡體": "zh-CN", "簡中": "zh-CN", "zh-cn": "zh-CN", "zh-hans": "zh-CN",
    # Other common languages
    "日文": "ja", "日語": "ja", "japanese": "ja",
    "韓文": "ko", "韓語": "ko", "korean": "ko",
    "西班牙文": "es", "西班牙語": "es", "spanish": "es",
    "法文": "fr", "法語": "fr", "french": "fr",
    "德文": "de", "德語": "de", "german": "de",
    "義大利文": "it", "意大利文": "it", "義語": "it", "italian": "it",
    "葡萄牙文": "pt", "葡語": "pt", "portuguese": "pt",
    "俄文": "ru", "俄語": "ru", "russian": "ru",
    "泰文": "th", "泰語": "th", "thai": "th",
    "越南文": "vi", "越南語": "vi", "vietnamese": "vi",
    "印尼文": "id", "印尼語": "id", "indonesian": "id",
    "阿拉伯文": "ar", "阿拉伯語": "ar", "arabic": "ar",
}


def resolveLanguage(languageName: str) -> str:

    """
    Turn a language name into a language code.
    Example: "繁體中文" -> "zh-TW", "Japanese" -> "ja". Unknown names are returned unchanged.
    """

    cleanName = languageName.strip()
    return LANGUAGE_ALIASES.get(cleanName.lower(), cleanName)


def getCachePath(targetLanguage: str, cacheDir: str = DEFAULT_CACHE_DIR) -> str:
    return os.path.join(cacheDir, f"{targetLanguage}.json")


def loadTranslationCache(targetLanguage: str, cacheDir: str = DEFAULT_CACHE_DIR) -> dict:

    """
    Load the saved translations {word: translation} for a language. Returns {} if there are none.
    """

    cachePath = getCachePath(targetLanguage, cacheDir)
    if not os.path.exists(cachePath):
        return {}

    try:
        with open(cachePath, encoding="utf-8") as cacheFile:
            cache = json.load(cacheFile)
    except (OSError, ValueError):
        return {}

    if not isinstance(cache, dict):
        return {}

    return cache


def saveTranslationCache(targetLanguage: str, cache: dict, cacheDir: str = DEFAULT_CACHE_DIR) -> None:
    os.makedirs(cacheDir, exist_ok=True)

    with open(getCachePath(targetLanguage, cacheDir), "w", encoding="utf-8") as cacheFile:
        json.dump(cache, cacheFile, ensure_ascii=False, indent=2)


def createTranslators(translatorChoice: str, sourceLanguage: str, targetLanguage: str) -> list[tuple]:

    """
    Create the translation services to try, in order.
    Returns:
        list[tuple]: [(service name, function word -> translation), ...]
    """

    translators = []

    for eachName in TRANSLATOR_ORDER[translatorChoice]:
        if eachName == "google":
            translate = connectGoogleTranslate.createGoogleTranslator(sourceLanguage, targetLanguage)
        else:
            def translate(word, target=targetLanguage, source=sourceLanguage):
                return connectMyMemory.translateWithMyMemory(word, target, source)

        if translate is not None:
            translators.append((TRANSLATOR_NAMES[eachName], translate))

    return translators


def isRateLimitError(error: Exception) -> bool:
    return type(error).__name__ in RATE_LIMIT_ERROR_NAMES or "too many requests" in str(error).lower()


def translateOneWord(translate, word: str) -> str:

    """
    Translate one word with one service. When the service answers "too many requests",
    wait and try again (1s, 2s, 4s). Other errors, or a word that still fails after every retry, raise the error.
    """

    retryDelay = FIRST_RETRY_DELAY

    for attempt in range(MAX_RETRIES + 1):
        try:
            return translate(word) or ""
        except Exception as error:
            if attempt == MAX_RETRIES or not isRateLimitError(error):
                raise

            time.sleep(retryDelay)
            retryDelay *= 2

    return ""


def translateWords(
    words: list[str],
    targetLanguage: str,
    sourceLanguage: str = "en",
    cacheDir: str = DEFAULT_CACHE_DIR,
    translatorChoice: str = "auto",
) -> dict:

    """
    Translate words (not definitions). Results are cached, so a word is only requested once
    and can be translated offline afterwards.
    Parameters:
        Mandatory:
            - words (list[str]): The words to translate.
            - targetLanguage (str): Target language code, e.g. "zh-TW".
        Optional:
            - sourceLanguage (str): Source language code.
            - cacheDir (str): Folder for the translation cache (relative to the current working directory).
            - translatorChoice (str): "auto" (Google, then MyMemory if Google stops answering), "google" or "mymemory".
        Default:
            - sourceLanguage: "en"
            - cacheDir: "translation_cache"
            - translatorChoice: "auto"
    Returns:
        dict: {word: translation} for every word that has a translation.
        Words that could not be translated (e.g. no network) are left out and are retried next time.
    """

    cache = loadTranslationCache(targetLanguage, cacheDir)
    missingWords = [eachWord for eachWord in words if not cache.get(eachWord)]

    if len(missingWords) > 0:
        translators = createTranslators(translatorChoice, sourceLanguage, targetLanguage)
        newTranslations = translateMissingWords(translators, missingWords)

        if len(newTranslations) > 0:
            cache.update(newTranslations)
            saveTranslationCache(targetLanguage, cache, cacheDir)

    return {eachWord: cache[eachWord] for eachWord in words if cache.get(eachWord)}


def translateMissingWords(translators: list[tuple], words: list[str]) -> dict:

    """
    Translate words one at a time. Each word is tried with the services in order, and the next service
    is used when one has no translation. A service that is rate limited (or fails MAX_CONSECUTIVE_FAILURES
    words in a row) is dropped for the rest of the run, so a blocked service is not hammered.
    Returns {word: translation} for the words that succeeded.
    """

    translations = {}
    activeTranslators = list(translators)
    failureCounts = {eachName: 0 for eachName, eachFunction in translators}

    for index, eachWord in enumerate(words):
        if len(activeTranslators) == 0:
            print(ChatColor.paint("No translation service is answering. Try again later.", ChatColor.ORANGE))
            break

        if index > 0:
            time.sleep(DELAY_BETWEEN_WORDS)

        for eachName, eachFunction in list(activeTranslators):
            try:
                translation = translateOneWord(eachFunction, eachWord)
            except Exception as error:
                failureCounts[eachName] += 1

                if isRateLimitError(error) or failureCounts[eachName] >= MAX_CONSECUTIVE_FAILURES:
                    activeTranslators.remove((eachName, eachFunction))
                    reportStoppedTranslator(eachName, error, activeTranslators)

                continue

            failureCounts[eachName] = 0
            if translation != "":
                translations[eachWord] = translation
                break

    return translations


def reportStoppedTranslator(name: str, error: Exception, remainingTranslators: list[tuple]) -> None:
    message = f"{name} stopped answering ({type(error).__name__})"

    if len(remainingTranslators) > 0:
        message += f", switching to {remainingTranslators[0][0]}."
    else:
        message += "."

    print(ChatColor.paint(message, ChatColor.ORANGE))


if __name__ == "__main__":
    print(translateWords(["ambiguous", "scrutinize"], resolveLanguage("繁體中文")))
