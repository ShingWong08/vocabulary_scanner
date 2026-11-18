# CEFR Vocabulary Level Scanner for English Documents

[中文](README.md) | **English**

Scans PDF, Word, Excel, images, and plain text files, determines the CEFR level (A1–C2) of every English word,
and automatically collects the advanced **B2–C2** words and phrases into a vocabulary book with English
definitions and example sentences taken from the source.

## Features

- Supports PDF (.pdf), Word (.docx), Excel (.xlsx), images (.png/.jpg/.tiff), and plain text (.txt/.csv/.md/.html)
- Accepts a single file, multiple files, or an entire folder (scanned recursively)
- Handles scanned PDFs: automatically detects PDFs with no text layer and falls back to Apple Vision OCR (macOS only)
- Bundled CEFR dictionary (A1–C2, ~10,000 hand-labelled entries from CEFR-J 1.6 + Octanove), plus estimated
  levels for ~68,000 more words (Maximax67) to fill the gaps; sources listed in `data/SOURCES.md`
- Lemmatization (run/runs/ran → run) and English definitions (WordNet, works offline)
- Optional translation: translate each word into a target language (Traditional Chinese, Simplified Chinese, Japanese, Korean, Spanish, French, etc.), translating only the word itself
- Multiple export formats for importing into dictionaries or flashcard apps

## Project Layout

```
vocabulary_scanner/
├── pyproject.toml                  package settings and dependencies
├── src/vocabulary_scanner/
│   ├── __init__.py                 command line program main()
│   ├── __main__.py                 makes python -m vocabulary_scanner work
│   ├── chatColor.py                colored terminal output
│   ├── cefrDictionary.py           CEFR dictionary and level lookup
│   ├── connectWordNet.py           WordNet lemmatization and definitions
│   ├── translation.py              translation: cache, language names, switching services
│   ├── connectGoogleTranslate.py   Google Translate
│   ├── connectMyMemory.py          MyMemory (fallback when Google is blocked)
│   ├── extractText.py              read PDF / Word / Excel / HTML / text files
│   ├── visionOCR.py                Apple Vision OCR (macOS)
│   ├── visionOCR.swift             source of the OCR helper
│   ├── scanText.py                 sentence splitting, word and phrase matching
│   ├── exportVocabularyBook.py     export Excel / CSV / Anki / Eudic / JSON / report
│   ├── buildDictionary.py          rebuild the dictionaries from the raw word lists
│   └── data/
│       ├── cefr_words.csv          main CEFR dictionary (CEFR-J + Octanove)
│       ├── cefr_words_estimated.csv estimated levels (Maximax67)
│       └── THIRD_PARTY_NOTICES.md  sources and licenses of the dictionary data
├── data/                           raw word lists (CEFR-J 1.6, Octanove) and source notes
├── sample/                         sample files
└── tests/                          pytest tests
```

## Installation

Requires Python 3.10 or newer.

### From PyPI

```bash
python -m pip install vocabulary-scanner
python -m nltk.downloader wordnet omw-1.4
```

All required packages, including `deep-translator` and `requests` for translation, are installed automatically.
On macOS, install `"vocabulary-scanner[ocr]"` to enable OCR.

### From source

Run these in the project folder:

**Windows (PowerShell)**

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
python -m pip install -e .
python -m nltk.downloader wordnet omw-1.4
```

**macOS / Linux**

```bash
python3 -m venv env
source env/bin/activate
python3 -m pip install -e ".[ocr]"
python3 -m nltk.downloader wordnet omw-1.4
```

- The translation packages (`deep-translator`, `requests`) are required dependencies and install automatically;
  the old `[translate]` extra still works but is no longer needed.
- `[ocr]`: OCR for scanned PDFs, macOS only.
- `[dev]`: `pytest` for development.
- `requirements.txt` in the project root lists the same dependencies (core + translation + OCR on macOS), so
  `python -m pip install -r requirements.txt` also works; you still need `pip install -e .` above for the `vocab-scanner` command.
- The last line downloads WordNet (once), used for definitions and lemmatization. If you skip it, the program tries to download it on its first run.

> If nltk cannot be installed or WordNet cannot be downloaded, the program still runs — it simply skips
> lemmatization and English definitions and falls back to matching the surface form. The CEFR-J dictionary
> already contains many inflected forms, so coverage remains reasonably good.

Each time you open a new terminal, activate the environment first (Windows: `.\env\Scripts\Activate.ps1`; macOS: `source env/bin/activate`).

### OCR (macOS, optional)

OCR uses Apple's built-in Vision framework, so Tesseract is not needed. Requirements:

- macOS with **Xcode Command Line Tools** (`swiftc` available). Run `xcode-select --install` in Terminal.
- On first use, the program compiles `visionOCR.swift` into `~/.cache/vocabulary_scanner/` automatically.

OCR only triggers when a PDF has **no text layer** (`--ocr auto`, the default). Native text PDFs never go
through OCR, so their speed is unaffected. **OCR is not supported on Windows**: images and scanned PDFs are
skipped, while all other formats work normally.

### Translation (optional)

Translation requires a network connection. By default (`--translator auto`) it uses Google Translate via
`deep-translator`, and switches to [MyMemory](https://mymemory.translated.net/) automatically when Google stops
answering (e.g. `TooManyRequests`). Results are cached in `translation_cache/` in the current folder, so the same
words can be translated offline afterwards. Words that fail to translate never stop the scan; they are retried
automatically on the next run.

- Google sometimes flags a computer that sent many requests as "unusual traffic" and blocks it for a while
  (usually a few hours to a day).
- MyMemory is free and needs no account, but has a free limit of about 5,000 characters per day (a few hundred
  words); it resets the next day.
- To pick a service: `--translator google` or `--translator mymemory`.

## Usage

Installing the package adds a `vocab-scanner` command (`python -m vocabulary_scanner` does the same thing).

### The easiest way: never type a path by hand

Paths that contain spaces (e.g. `Group 6_TAM ... Final Version.docx`) must be quoted, and a single missing
quote is enough to make the command fail. The simplest approach is to let the terminal paste the path for you:

1. Type `vocab-scanner`, **leaving a trailing space**
2. Drag the file (or a whole folder) from File Explorer (Windows) or Finder (macOS) into the terminal window — the path is pasted automatically
3. Press Enter

> Every option is optional. Results go to `output/` in the current folder by default; `--out-dir` changes the
> output folder so a previous run is not overwritten, e.g. `--out-dir output/essay`.

### Command examples

```bash
# Scan an entire folder
vocab-scanner sample/

# Scan multiple files
vocab-scanner report.pdf notes.docx data.xlsx

# Merge into an existing vocabulary book (accumulate counts, keep sources)
vocab-scanner new_docs/ --merge output/vocabulary_book.csv

# Look up the level of a single word
vocab-scanner --lookup ambiguous

# Scan and translate the words into Traditional Chinese (words only, not definitions)
vocab-scanner sample/ --translate zh-TW

# Language names or codes both work, e.g. zh-CN (Simplified Chinese), ja (Japanese), ko (Korean), es (Spanish), fr (French)
vocab-scanner sample/ --translate 日文

# Force OCR for every PDF (macOS, usually unnecessary)
vocab-scanner scans/ --ocr force

# Disable OCR entirely
vocab-scanner scans/ --ocr off
```

## Options

| Option | Description | Default |
|------|------|------|
| `inputs` | Files or folders (multiple allowed) | none |
| `--out-dir` | Output folder | `output` |
| `--min-level` | Lowest level included in the vocabulary book | `B2` |
| `--max-level` | Highest level included in the vocabulary book | `C2` |
| `--merge` | Merge into an existing `vocabulary_book.csv` | none |
| `--sort` | `level` = by level (A1→A2→B1→B2→C1→C2), then alphabetically; `count` = by frequency | `level` |
| `--top` | Number of unknown words listed in the report | `30` |
| `--no-definitions` | Skip WordNet English definitions (lemmatization is still used) | none |
| `--no-estimated` | Only use the hand-labelled CEFR-J / Octanove levels, no estimated levels | none |
| `--lookup` | Look up one word's level, then exit | none |
| `--ocr` | OCR mode: `auto` = only when there is no text layer, `force` = always OCR PDFs, `off` = disabled | `auto` |
| `--ocr-dpi` | Resolution used to render PDF pages for OCR | `200` |
| `--translate` | Translate words into the given language (`zh-TW`, `zh-CN`, `ja`, `ko`, `es`, `fr`, …); words only | none |
| `--translator` | Translation service: `auto` = Google, then MyMemory if Google stops answering; `google`; `mymemory` | `auto` |
| `--translation-cache` | Folder for cached translations | `translation_cache` |
| `--dictionary` | Use a different CEFR dictionary CSV | bundled dictionary |

## Output (written to `output/` by default)

| File | Purpose |
|------|------|
| `vocabulary_book.xlsx` | Excel vocabulary book (includes a "Translation" column and a level statistics sheet) |
| `vocabulary_book.csv` | CSV vocabulary book; use this file with `--merge` |
| `vocabulary_anki.tsv` | Anki import file (word / definition / example / level / part of speech / translation) |
| `vocabulary_eudic.txt` | Word list for Eudic, Youdao, and similar apps (one word per line) |
| `vocabulary_book.json` | JSON format |
| `analysis_report.txt` | Full analysis report (level distribution + vocabulary book + common unknown words) |

## Importing into Dictionaries / Flashcard Apps

- **Anki**: File → Import → select `vocabulary_anki.tsv`, set the separator to "Tab",
  then map the fields to word, definition, example, level, part of speech, and translation.
- **Eudic**: Learning → Vocabulary Book → Import → select `vocabulary_eudic.txt` (one word per line).
- **Youdao / others**: Most apps accept a `.txt` with one word per line, so `vocabulary_eudic.txt` works there too.

## Level Assignment Rules

- A word is first matched on its lowercase, accent-stripped surface form; if that fails, it is lemmatized with
  WordNet and matched again.
- If a word appears in several levels, the **lower** level wins (following the CEFR convention that a word is
  acquired at the earliest level it appears in), while `all_levels` retains every level.
- Phrases (e.g. `climate change`) are matched as 2–4 word sequences and listed separately from single words.
- Words missing from the main dictionary fall back to the estimated dictionary (Maximax67). They are marked
  "推算" in the Excel "推算等級" column and get a `*` after the level in the Anki file and the report (e.g. `C2*`).
  Treat these levels as rough guides; `--no-estimated` turns the fallback off.
- Web addresses, DOIs and e-mail addresses are removed before scanning, so they are not counted as words.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Rebuild the CEFR dictionary: `python -m vocabulary_scanner.buildDictionary` (see `data/SOURCES.md`).

## Notes

- Legacy Word `.doc` and Excel `.xls` files are not supported directly; save them as `.docx` / `.xlsx` first.
- Scanned PDFs are processed with OCR automatically (macOS); a higher resolution (`--ocr-dpi`) is more accurate but
  slower, so be patient with long documents.
- Translation requires network access; the first batch of new words is slow, but later runs hit the cache
  (`translation_cache/`) and are fast.
- CEFR levels are approximate: the same word can sit at different levels in different contexts or parts of speech.
