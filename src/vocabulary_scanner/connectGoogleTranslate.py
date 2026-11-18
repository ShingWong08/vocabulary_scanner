from vocabulary_scanner.chatColor import ChatColor


def createGoogleTranslator(sourceLanguage: str, targetLanguage: str):

    """
    Create a function that translates one word with Google Translate (via deep-translator).
    Parameters:
        Mandatory:
            - sourceLanguage (str): Source language code, e.g. "en".
            - targetLanguage (str): Target language code, e.g. "zh-TW".
    Returns:
        A function word -> translation, or None if deep-translator is not installed
        or does not support the language.
    """

    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        print(ChatColor.paint("deep-translator is not installed, so Google Translate is skipped.", ChatColor.ORANGE))
        return None

    try:
        translator = GoogleTranslator(source=sourceLanguage, target=targetLanguage)
    except Exception as error:
        print(ChatColor.paint(f"Google Translate cannot be used: {error}", ChatColor.ORANGE))
        return None

    def translateWithGoogle(word: str) -> str:
        return translator.translate(word) or ""

    return translateWithGoogle


if __name__ == "__main__":
    translate = createGoogleTranslator("en", "zh-TW")
    if translate is not None:
        print(translate("ambiguous"))
