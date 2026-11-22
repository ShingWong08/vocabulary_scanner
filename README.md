# CEFR Vocabulary Level Scanner for English Documents

[中文](README.zh-hk.md) | **English**

## Overview

A command line tool that scans PDF, Word, Excel, image and plain text files, determines the CEFR level (A1–C2)
of every English word, and automatically collects the advanced **B2–C2** words and phrases into a vocabulary book
with English definitions and example sentences taken from the source.
The vocabulary book can be exported to Excel, CSV, Anki, Eudic and other formats for importing into dictionaries
or flashcard apps.

> [!NOTE]
> OCR for scanned PDFs is macOS only. On Windows, image files and PDFs without a text layer are skipped;
> all other formats work normally.

---

## Requirements

- Python 3.10 or newer
- pip
- (Optional) Xcode Command Line Tools on macOS: needed for OCR
- (Optional) A network connection: needed for translation

---

## Setup

> [!NOTE]
> You can also install straight from PyPI: `python -m pip install vocabulary-scanner`.
> On macOS, install `"vocabulary-scanner[ocr]"` to enable OCR. Either way, run step 3 below to download WordNet.

1. **Create and activate a virtual environment:**

    Windows (PowerShell)

    ```powershell
    python -m venv env
    .\env\Scripts\Activate.ps1
    ```

    macOS / Linux

    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

2. **Install the package:**

    Windows

    ```powershell
    python -m pip install -e .
    ```

    macOS (with OCR)

    ```bash
    python3 -m pip install -e ".[ocr]"
    ```

3. **Download the WordNet data (once):**

    ```
    python -m nltk.downloader wordnet omw-1.4
    ```

    WordNet provides English definitions and lemmatization. If you skip this step, the program tries to download
    it on its first run; even if that fails, the program still runs, just without lemmatization and definitions.

4. **Start scanning:**

    ```
    vocab-scanner sample/
    ```

    The results are written to `output/` in the current folder.

Each time you open a new terminal, activate the virtual environment first (the second line of step 1).

---

## Usage

Installing the package adds a `vocab-scanner` command (`python -m vocabulary_scanner` does the same thing).

> [!TIP]
> Paths that contain spaces must be quoted, which is easy to get wrong by hand. Type `vocab-scanner`
> (**leaving a trailing space**), then drag the file or folder from File Explorer / Finder into the terminal
> so the path is pasted for you, and press Enter.

```bash
# Scan an entire folder
vocab-scanner sample/

# Scan multiple files
vocab-scanner report.pdf notes.docx data.xlsx

# Write to a different folder so the previous results are not overwritten
vocab-scanner essay.docx --out-dir output/essay

# Merge into an existing vocabulary book (accumulate counts, keep sources)
vocab-scanner new_docs/ --merge output/vocabulary_book.csv

# Look up the level of a single word
vocab-scanner --lookup ambiguous

# Translate the words into Traditional Chinese (words only, not definitions)
vocab-scanner sample/ --translate zh-TW

# Language names or codes both work, e.g. zh-CN, ja, ko, es, fr
vocab-scanner sample/ --translate 日文

# Force OCR for every PDF (macOS, usually unnecessary) / disable OCR entirely
vocab-scanner scans/ --ocr force
vocab-scanner scans/ --ocr off
```

---

## Options

Every option is optional.

| Option | Description | Default |
|------|------|------|
| `inputs` | Files or folders (multiple allowed) | none |
| `--out-dir` | Output folder | `output` |
| `--min-level` | Lowest level included in the vocabulary book | `B2` |
| `--max-level` | Highest level included in the vocabulary book | `C2` |
| `--merge` | Merge into an existing `vocabulary_book.csv` | none |
| `--sort` | `level` = by level (A1→C2), then alphabetically; `count` = by frequency | `level` |
| `--top` | Number of unknown words listed in the report | `30` |
| `--no-definitions` | Skip WordNet English definitions (lemmatization is still used) | none |
| `--no-estimated` | Only use the hand-labelled CEFR-J / Octanove levels, no estimated levels | none |
| `--lookup` | Look up one word's level, then exit | none |
| `--ocr` | `auto` = only when there is no text layer; `force` = always OCR PDFs; `off` = disabled | `auto` |
| `--ocr-dpi` | Resolution used to render PDF pages for OCR | `200` |
| `--translate` | Translate words into the given language (`zh-TW`, `zh-CN`, `ja`, `ko`, `es`, `fr`, …) | none |
| `--translator` | `auto` = Google, then MyMemory if Google stops answering; `google`; `mymemory` | `auto` |
| `--translation-cache` | Folder for cached translations | `translation_cache` |
| `--dictionary` | Use a different CEFR dictionary CSV | bundled dictionary |

---

## Features

- Supports PDF (.pdf), Word (.docx), Excel (.xlsx), images (.png/.jpg/.tiff) and plain text (.txt/.csv/.md/.html)
- Accepts a single file, multiple files, or an entire folder (scanned recursively)
- Detects PDFs with no text layer and reads them with Apple Vision OCR (macOS only, no Tesseract needed)
- Bundled CEFR dictionary: ~10,000 hand-labelled entries (CEFR-J 1.6 + Octanove),
  plus estimated levels for ~68,000 more words (Maximax67) to fill the gaps
- Lemmatization (run/runs/ran → run) and English definitions (WordNet, works offline)
- Phrase matching (e.g. `climate change`), listed separately from single words
- Optional translation: Google Translate, switching to MyMemory automatically when blocked, with caching
- Exports Excel, CSV, Anki, Eudic, JSON and an analysis report

---

## Output Files

Results are written to `output/` by default:

| File | Purpose |
|------|------|
| `vocabulary_book.xlsx` | Excel vocabulary book (includes a "Translation" column and a level statistics sheet) |
| `vocabulary_book.csv` | CSV vocabulary book; use this file with `--merge` |
| `vocabulary_anki.tsv` | Anki import file (word / definition / example / level / part of speech / translation) |
| `vocabulary_eudic.txt` | Word list for Eudic, Youdao and similar apps (one word per line) |
| `vocabulary_book.json` | JSON format |
| `analysis_report.txt` | Full analysis report (level distribution + vocabulary book + common unknown words) |

**Importing into flashcard apps**

- **Anki**: File → Import → select `vocabulary_anki.tsv`, set the separator to "Tab", then map the fields to word, definition, example, level, part of speech and translation.
- **Eudic**: Learning → Vocabulary Book → Import → select `vocabulary_eudic.txt`.
- **Youdao / others**: Most apps accept a `.txt` with one word per line, so `vocabulary_eudic.txt` works there too.

---

## Project Structure

```
vocabulary_scanner/
├── pyproject.toml                   # package settings and dependencies
├── requirements.txt                 # the same dependency list (for pip install -r)
├── src/vocabulary_scanner/
│   ├── __init__.py                  # command line program main()
│   ├── __main__.py                  # makes python -m vocabulary_scanner work
│   ├── chatColor.py                 # colored terminal output
│   ├── cefrDictionary.py            # CEFR dictionary and level lookup
│   ├── connectWordNet.py            # WordNet lemmatization and definitions
│   ├── translation.py               # translation: cache, language names, switching services
│   ├── connectGoogleTranslate.py    # Google Translate
│   ├── connectMyMemory.py           # MyMemory (fallback when Google is blocked)
│   ├── extractText.py               # read PDF / Word / Excel / HTML / text files
│   ├── visionOCR.py                 # Apple Vision OCR (macOS)
│   ├── visionOCR.swift              # source of the OCR helper
│   ├── scanText.py                  # sentence splitting, word and phrase matching
│   ├── exportVocabularyBook.py      # export Excel / CSV / Anki / Eudic / JSON / report
│   ├── buildDictionary.py           # rebuild the dictionaries from the raw word lists
│   └── data/
│       ├── cefr_words.csv           # main CEFR dictionary (CEFR-J + Octanove)
│       ├── cefr_words_estimated.csv # estimated levels (Maximax67)
│       └── THIRD_PARTY_NOTICES.md   # sources and licenses of the dictionary data
├── data/                            # raw word lists and source notes (SOURCES.md)
├── sample/                          # sample files
└── tests/                           # pytest tests
```

---

## Level Assignment Rules

- A word is first matched on its lowercase, accent-stripped surface form; if that fails, it is lemmatized with
  WordNet and matched again.
- If a word appears in several levels, the **lower** level wins (CEFR convention), while `all_levels` keeps every level.
- Phrases are matched as 2–4 word sequences.
- Words missing from the main dictionary fall back to the estimated dictionary. They are marked "推算" in the
  Excel "推算等級" column and get a `*` after the level in the Anki file and the report (e.g. `C2*`); treat these
  levels as rough guides. `--no-estimated` turns the fallback off.
- Web addresses, DOIs and e-mail addresses are removed before scanning, so they are not counted as words.

---

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Rebuild the CEFR dictionary: `python -m vocabulary_scanner.buildDictionary` (see `data/SOURCES.md`).

---

## Notes

- Legacy Word `.doc` and Excel `.xls` files are not supported directly; save them as `.docx` / `.xlsx` first.
- On first use, OCR compiles `visionOCR.swift` into `~/.cache/vocabulary_scanner/`, which needs `swiftc`
  (run `xcode-select --install` in Terminal). A higher `--ocr-dpi` is more accurate but slower.
- Translations are cached in `translation_cache/`, so the same words work offline afterwards; words that fail to
  translate never stop the scan and are retried on the next run.
- Google Translate sometimes blocks a computer for a while after many requests (usually a few hours to a day);
  MyMemory has a free limit of about 5,000 characters per day. Use `--translator` to pick a service.
- CEFR levels are approximate: the same word can sit at different levels in different contexts or parts of speech.
- If you run into problems, check that you are on Python 3.10 or newer and that the virtual environment is
  active, then run `python -m pip install -e .` again.
