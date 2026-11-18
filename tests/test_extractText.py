import os

from vocabulary_scanner import extractText


def test_collect_input_files_is_recursive_and_sorted(tmp_path):
    (tmp_path / "b").mkdir()
    (tmp_path / "a").mkdir()
    (tmp_path / "b" / "two.txt").write_text("x")
    (tmp_path / "a" / "one.md").write_text("x")
    (tmp_path / "skip.exe").write_text("x")

    files = extractText.collectInputFiles([str(tmp_path), str(tmp_path / "missing.txt")])

    assert files == [
        os.path.join(tmp_path, "a", "one.md"),
        os.path.join(tmp_path, "b", "two.txt"),
    ]


def test_reads_utf8_and_windows_1252_text(tmp_path):
    utf8File = tmp_path / "utf8.txt"
    utf8File.write_text("Café don’t", encoding="utf-8")
    ansiFile = tmp_path / "ansi.txt"
    ansiFile.write_bytes("Café don’t".encode("cp1252"))

    assert extractText.extractText(str(utf8File)) == "Café don’t"
    assert extractText.extractText(str(ansiFile)) == "Café don’t"


def test_html_keeps_only_visible_text(tmp_path):
    page = tmp_path / "page.html"
    page.write_text(
        "<html><head><style>body {color: red}</style><script>var x = 1;</script></head>"
        "<body><p class='intro'>Tom &amp; Jerry</p></body></html>",
        encoding="utf-8",
    )

    words = extractText.extractText(str(page)).split()
    assert words == ["Tom", "&", "Jerry"]


def test_images_are_skipped_without_ocr(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(extractText.visionOCR, "isOCRAvailable", lambda: False)
    image = tmp_path / "scan.png"
    image.write_bytes(b"")

    assert extractText.extractText(str(image)) == ""
    assert "only works on macOS" in capsys.readouterr().out


def test_sample_files_can_be_read():
    for eachName in ["sample_text.txt", "sample_doc.docx", "sample_data.xlsx", "sample.pdf"]:
        text = extractText.extractText(f"sample/{eachName}", ocrMode="off")
        assert len(text.strip()) > 0, eachName
