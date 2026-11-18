import pytest
import requests

from vocabulary_scanner import connectMyMemory


class FakeResponse:
    def __init__(self, data=None, status_code=200):
        if data is None:
            data = {}

        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def answer(translatedText, responseStatus=200, quotaFinished=False):
    return {
        "responseData": {"translatedText": translatedText},
        "responseStatus": responseStatus,
        "quotaFinished": quotaFinished,
    }


@pytest.fixture
def captured(monkeypatch):
    calls = {}

    def fakeGet(url, params, timeout):
        calls["url"] = url
        calls["params"] = params
        calls["timeout"] = timeout
        return calls.get("response", FakeResponse(answer("歧義")))

    monkeypatch.setattr(connectMyMemory.requests, "get", fakeGet)
    return calls


def test_translates_word(captured):
    assert connectMyMemory.translateWithMyMemory(" ambiguous ", "zh-TW") == "歧義"
    assert captured["params"] == {"q": "ambiguous", "langpair": "en|zh-TW"}
    assert captured["timeout"] == 15


def test_same_word_back_means_no_translation(captured):
    captured["response"] = FakeResponse(answer("Ambiguous"))
    assert connectMyMemory.translateWithMyMemory("ambiguous", "zh-TW") == ""


@pytest.mark.parametrize("response", [
    FakeResponse(status_code=429),
    FakeResponse(answer("x", quotaFinished=True)),
    FakeResponse(answer("x", responseStatus=429)),
    FakeResponse(answer("MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY.")),
])
def test_daily_limit_raises(captured, response):
    captured["response"] = response
    with pytest.raises(connectMyMemory.MyMemoryLimitError):
        connectMyMemory.translateWithMyMemory("ambiguous", "zh-TW")


def match(segment, translation, createdBy):
    return {"segment": segment, "translation": translation, "created-by": createdBy}


def test_machine_translation_is_preferred(captured):
    data = answer("限制結果集，除了那些有特定母ID的項目。")
    data["matches"] = [
        match("Particular", "限制結果集，除了那些有特定母ID的項目。", "MateCat"),
        match("particular", "特別", "MT!"),
    ]
    captured["response"] = FakeResponse(data)

    assert connectMyMemory.translateWithMyMemory("particular", "zh-TW") == "特別"


def test_exact_match_is_used_without_machine_translation(captured):
    data = answer("<g>次級</g>")
    data["matches"] = [
        match("Secondary school", "中學", "MateCat"),
        match("Secondary", "次要的", "MateCat"),
    ]
    captured["response"] = FakeResponse(data)

    assert connectMyMemory.translateWithMyMemory("secondary", "zh-TW") == "次要的"


def test_unusable_candidates_are_skipped():
    matches = [match("secondly", "2", "MT!"), match("Secondly", "其次", "Wikipedia")]
    assert connectMyMemory.chooseTranslation("secondly", "2", matches) == "其次"
    assert connectMyMemory.chooseTranslation("secondly", "2", []) == ""


@pytest.mark.parametrize("text, cleaned", [
    ("<g>次級</g>", "次級"),
    ("&診斷測試($Diagnostic)", "診斷測試"),
    ("［預防］:", "預防"),
    ("混亂！", "混亂"),
    ("精神病的；精神病學的", "精神病的；精神病學的"),
    ("2", ""),
    ("  ", ""),
])
def test_clean_translation(text, cleaned):
    assert connectMyMemory.cleanTranslation(text) == cleaned


def test_server_error_raises(captured):
    captured["response"] = FakeResponse(status_code=500)
    with pytest.raises(requests.HTTPError):
        connectMyMemory.translateWithMyMemory("ambiguous", "zh-TW")


def test_empty_word_raises():
    with pytest.raises(ValueError):
        connectMyMemory.translateWithMyMemory("  ", "zh-TW")
