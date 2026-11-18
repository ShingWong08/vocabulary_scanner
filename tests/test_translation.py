import pytest

from vocabulary_scanner import translation


class TooManyRequests(Exception):
    pass


class FakeService:

    """
    Words in `failingWords` always fail. The first `rateLimitedCalls` requests answer "too many requests".
    Translations are the word in upper case plus `suffix`; words in `unknownWords` get "".
    """

    def __init__(self, suffix="", failingWords=(), rateLimitedCalls=0, unknownWords=()):
        self.suffix = suffix
        self.failingWords = set(failingWords)
        self.rateLimitedCalls = rateLimitedCalls
        self.unknownWords = set(unknownWords)
        self.requested = []

    def translate(self, word):
        self.requested.append(word)

        if self.rateLimitedCalls > 0:
            self.rateLimitedCalls -= 1
            raise TooManyRequests("You made too many requests to the server.")

        if word in self.failingWords:
            raise ConnectionError("offline")

        if word in self.unknownWords:
            return ""

        return word.upper() + self.suffix


@pytest.fixture
def sleeps(monkeypatch):
    waited = []
    monkeypatch.setattr(translation.time, "sleep", waited.append)
    return waited


@pytest.fixture
def google(monkeypatch, sleeps):
    service = FakeService(failingWords={"addicted"})
    monkeypatch.setattr(translation, "createTranslators", lambda choice, source, target: [("Google", service.translate)])
    return service


@pytest.fixture
def googleAndMyMemory(monkeypatch, sleeps):
    services = {"google": FakeService(), "mymemory": FakeService(suffix="!")}
    monkeypatch.setattr(
        translation,
        "createTranslators",
        lambda choice, source, target: [("Google", services["google"].translate), ("MyMemory", services["mymemory"].translate)],
    )
    return services


def test_failed_word_does_not_crash(google, tmp_path):
    # Used to raise KeyError: 'addicted'
    result = translation.translateWords(["addicted", "cat"], "zh-TW", cacheDir=str(tmp_path))
    assert result == {"cat": "CAT"}


def test_rate_limit_is_retried_with_backoff(google, sleeps, tmp_path):
    google.rateLimitedCalls = 2

    result = translation.translateWords(["cat"], "zh-TW", cacheDir=str(tmp_path))

    assert result == {"cat": "CAT"}
    assert google.requested == ["cat", "cat", "cat"]
    assert sleeps == [1.0, 2.0]


def test_stops_after_consecutive_failures(google, tmp_path, capsys):
    google.failingWords = {"a", "b", "c", "d", "e"}

    result = translation.translateWords(["a", "b", "c", "d", "e"], "zh-TW", cacheDir=str(tmp_path))

    assert result == {}
    assert google.requested == ["a", "b", "c"]
    out = capsys.readouterr().out
    assert "Google stopped answering" in out
    assert "No translation service is answering" in out


def test_words_are_spaced_out_for_the_rate_limit(google, sleeps, tmp_path):
    translation.translateWords(["cat", "dog", "pig"], "zh-TW", cacheDir=str(tmp_path))
    assert sleeps == [translation.DELAY_BETWEEN_WORDS] * 2


def test_blocked_google_switches_to_mymemory(googleAndMyMemory, tmp_path, capsys):
    googleAndMyMemory["google"].rateLimitedCalls = 100  # Google is blocked

    result = translation.translateWords(["cat", "dog"], "zh-TW", cacheDir=str(tmp_path))

    assert result == {"cat": "CAT!", "dog": "DOG!"}
    # Google is dropped after the first word (4 tries with backoff), not asked again for "dog"
    assert googleAndMyMemory["google"].requested == ["cat"] * 4
    assert "Google stopped answering (TooManyRequests), switching to MyMemory." in capsys.readouterr().out


def test_next_service_is_used_when_first_has_no_translation(googleAndMyMemory, tmp_path):
    googleAndMyMemory["google"].unknownWords = {"dog"}

    result = translation.translateWords(["cat", "dog"], "zh-TW", cacheDir=str(tmp_path))

    assert result == {"cat": "CAT", "dog": "DOG!"}


def test_translations_are_cached(google, tmp_path):
    translation.translateWords(["cat"], "zh-TW", cacheDir=str(tmp_path))
    google.requested.clear()

    result = translation.translateWords(["cat"], "zh-TW", cacheDir=str(tmp_path))

    assert result == {"cat": "CAT"}
    assert google.requested == []
    assert translation.loadTranslationCache("zh-TW", str(tmp_path)) == {"cat": "CAT"}


def test_failed_words_are_retried_next_time(google, tmp_path):
    translation.translateWords(["addicted"], "zh-TW", cacheDir=str(tmp_path))
    google.failingWords.clear()

    assert translation.translateWords(["addicted"], "zh-TW", cacheDir=str(tmp_path)) == {"addicted": "ADDICTED"}


def test_only_requested_words_are_returned(google, tmp_path):
    translation.saveTranslationCache("zh-TW", {"dog": "狗"}, str(tmp_path))
    assert translation.translateWords(["cat"], "zh-TW", cacheDir=str(tmp_path)) == {"cat": "CAT"}


def test_no_services_returns_cached_words_only(monkeypatch, tmp_path):
    monkeypatch.setattr(translation, "createTranslators", lambda choice, source, target: [])
    translation.saveTranslationCache("ja", {"cat": "猫"}, str(tmp_path))

    assert translation.translateWords(["cat", "dog"], "ja", cacheDir=str(tmp_path)) == {"cat": "猫"}


def test_broken_cache_file_is_ignored(tmp_path):
    (tmp_path / "ko.json").write_text("not json", encoding="utf-8")
    assert translation.loadTranslationCache("ko", str(tmp_path)) == {}


def test_translator_choice_controls_services(monkeypatch):
    monkeypatch.setattr(translation.connectGoogleTranslate, "createGoogleTranslator", lambda source, target: lambda word: "G")

    assert [name for name, function in translation.createTranslators("auto", "en", "zh-TW")] == ["Google Translate", "MyMemory"]
    assert [name for name, function in translation.createTranslators("google", "en", "zh-TW")] == ["Google Translate"]
    assert [name for name, function in translation.createTranslators("mymemory", "en", "zh-TW")] == ["MyMemory"]


def test_missing_deep_translator_still_uses_mymemory(monkeypatch):
    monkeypatch.setattr(translation.connectGoogleTranslate, "createGoogleTranslator", lambda source, target: None)
    assert [name for name, function in translation.createTranslators("auto", "en", "zh-TW")] == ["MyMemory"]


def test_resolve_language():
    assert translation.resolveLanguage("繁體中文") == "zh-TW"
    assert translation.resolveLanguage(" Japanese ") == "ja"
    assert translation.resolveLanguage("ZH-CN") == "zh-CN"
    assert translation.resolveLanguage("nl") == "nl"
