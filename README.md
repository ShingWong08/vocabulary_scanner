# 英文文件 CEFR 單詞等級掃描工具

**中文** | [English](README.en.md)

掃描 PDF、Word、Excel、圖片、純文字等檔案，分析每個英文單詞的 CEFR 等級（A1–C2），
並自動把 **B2 到 C2** 的高級單詞／片語整理成單詞簿，附英文定義與出處例句。

## 功能

- 支援 PDF（.pdf）、Word（.docx）、Excel（.xlsx）、圖片（.png/.jpg/.tiff）與純文字（.txt/.csv/.md/.html）
- 支援單一檔案或多個檔案／整個資料夾（遞迴掃描）
- 掃描圖片 PDF：自動偵測「沒有文字層」的 PDF，改用 Apple Vision OCR 認字（僅 macOS）
- 內建 CEFR 字典（A1–C2，約 1 萬筆人工標注詞條：CEFR-J 1.6 + Octanove），
  另有約 6.8 萬個單詞的推算等級（Maximax67），補足字典沒收錄的字；來源見 `data/SOURCES.md`
- 詞形還原（run/runs/ran → run）與英文定義（WordNet，可離線）
- 可選翻譯：把單詞翻譯成指定語言（繁中、簡中、日、韓、西、法等），只翻單詞本身
- 匯出多種格式，方便匯入字典或背單詞 App

## 專案結構

```
vocabulary_scanner/
├── pyproject.toml                  套件設定與相依套件
├── src/vocabulary_scanner/
│   ├── __init__.py                 命令列主程式 main()
│   ├── __main__.py                 讓 python -m vocabulary_scanner 可以執行
│   ├── chatColor.py                終端機彩色輸出
│   ├── cefrDictionary.py           CEFR 字典與等級查詢
│   ├── connectWordNet.py           WordNet 詞形還原與英文定義
│   ├── translation.py              翻譯：快取、語言名稱、自動切換翻譯服務
│   ├── connectGoogleTranslate.py   Google 翻譯
│   ├── connectMyMemory.py          MyMemory 翻譯（Google 被擋時的備援）
│   ├── extractText.py              讀取 PDF / Word / Excel / HTML / 文字檔
│   ├── visionOCR.py                Apple Vision OCR（macOS）
│   ├── visionOCR.swift             OCR 輔助程式原始碼
│   ├── scanText.py                 斷句、比對單詞與片語
│   ├── exportVocabularyBook.py     匯出 Excel / CSV / Anki / 欧路 / JSON / 報告
│   ├── buildDictionary.py          由原始詞表重建字典
│   └── data/
│       ├── cefr_words.csv          CEFR 主字典（CEFR-J + Octanove）
│       ├── cefr_words_estimated.csv 推算等級字典（Maximax67）
│       └── THIRD_PARTY_NOTICES.md  字典資料的來源與授權聲明
├── data/                           原始詞表（CEFR-J 1.6、Octanove）與資料來源說明
├── sample/                         範例檔案
└── tests/                          pytest 測試
```

## 安裝

需要 Python 3.10 以上。

### 從 PyPI 安裝

```bash
python -m pip install vocabulary-scanner
python -m nltk.downloader wordnet omw-1.4
```

所有必要套件（包括翻譯用的 `deep-translator` 與 `requests`）都會自動安裝。macOS 要使用 OCR 時改裝 `"vocabulary-scanner[ocr]"`。

### 從原始碼安裝

在專案資料夾執行：

**Windows（PowerShell）**

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

- 翻譯套件（`deep-translator`、`requests`）是必要套件，會自動安裝；舊指令裡的 `[translate]` 仍可使用，但已不需要。
- `[ocr]`：圖片 PDF 的 OCR，只在 macOS 有效。
- `[dev]`：開發用的 `pytest`。
- 專案根目錄的 `requirements.txt` 列出同樣的相依套件（核心＋翻譯＋macOS 的 OCR），
  也可以用 `python -m pip install -r requirements.txt` 安裝；但要使用 `vocab-scanner` 指令，仍需執行上面的 `pip install -e .`。
- 最後一行下載 WordNet（只需一次），用於英文定義與詞形還原。沒下載的話，程式第一次執行時也會自動嘗試下載。

> 若無法安裝 nltk 或下載 WordNet，程式仍可執行，只是會跳過「詞形還原」與「英文定義」，
> 改用單詞原形比對（CEFR-J 字典本身已含大量屈折形式，仍有相當涵蓋率）。

之後每次開新的終端機，先啟用虛擬環境（Windows：`.\env\Scripts\Activate.ps1`；macOS：`source env/bin/activate`）。

### OCR（macOS，選用）

OCR 使用 Apple 內建的 Vision 框架，不需要另外安裝 Tesseract。啟用條件：

- macOS 需有 **Xcode 命令列工具**（`swiftc` 可用）。終端機執行 `xcode-select --install` 即可安裝。
- 首次用到 OCR 時，程式會自動把 `visionOCR.swift` 編譯到 `~/.cache/vocabulary_scanner/`。

OCR 只在「PDF 沒有文字層」時才會觸發（`--ocr auto`，預設）；原生文字 PDF 完全不經過 OCR，速度不受影響。
**Windows 不支援 OCR**：圖片檔與掃描圖片 PDF 會被略過，其他格式不受影響。

### 翻譯（選用）

翻譯需要網路連線，預設（`--translator auto`）先用 Google 翻譯（`deep-translator`）；
Google 不回應時（例如回報 `TooManyRequests`），自動改用 [MyMemory](https://mymemory.translated.net/)。
翻譯結果會快取在目前資料夾的 `translation_cache/`，之後同樣的單詞離線也能用。
翻譯失敗的單詞不會中斷掃描，下次執行時會自動重試。

- Google 偶爾會把短時間內大量請求的電腦判定為「異常流量」並暫時封鎖（通常幾小時到一天後恢復）。
- MyMemory 免費、不需帳號，但每天約有 5,000 字元的免費額度（約數百個單詞），用完會在隔天恢復。
- 想指定翻譯服務：`--translator google` 或 `--translator mymemory`。

## 使用

安裝後會有 `vocab-scanner` 指令（也可以用 `python -m vocabulary_scanner`，效果相同）。

### 最省事的方法：完全不用手打路徑

路徑有空白時（例如 `Group 6_TAM ... Final Version.docx`）必須加引號，手動輸入很容易少一個引號就報錯。
最簡單的做法是讓終端機自己幫你貼：

1. 先輸入 `vocab-scanner`，**結尾留一個空格**
2. 從檔案總管（Windows）或 Finder（macOS）把檔案或整個資料夾拖進終端機視窗 → 路徑會自動貼上
3. 按 Enter

> 所有參數都是選填的。結果預設寫到目前資料夾的 `output/`；加 `--out-dir` 可以換一個輸出資料夾，
> 避免覆蓋上一次的結果，例如 `--out-dir output/essay`。

### 完整指令範例

```bash
# 掃描整個資料夾
vocab-scanner sample/

# 掃描多個檔案
vocab-scanner report.pdf notes.docx data.xlsx

# 合併進既有單詞簿（累加次數、保留來源）
vocab-scanner new_docs/ --merge output/vocabulary_book.csv

# 只查詢某個單詞的等級
vocab-scanner --lookup ambiguous

# 掃描並把單詞翻譯成繁體中文（只翻單詞，不翻定義）
vocab-scanner sample/ --translate zh-TW

# 支援語言名稱或代碼，例如：zh-CN（簡中）、ja（日）、ko（韓）、es（西）、fr（法）
vocab-scanner sample/ --translate 日文

# 強制所有 PDF 都用 OCR（macOS，通常不需要）
vocab-scanner scans/ --ocr force

# 完全關閉 OCR
vocab-scanner scans/ --ocr off
```

## 參數

| 參數 | 說明 | 預設 |
|------|------|------|
| `inputs` | 檔案或資料夾（可多個） | 無 |
| `--out-dir` | 輸出資料夾 | `output` |
| `--min-level` | 單詞簿最低等級 | `B2` |
| `--max-level` | 單詞簿最高等級 | `C2` |
| `--merge` | 合併進既有 `vocabulary_book.csv` | 無 |
| `--sort` | 排序方式：`level`＝先依等級（A1→A2→B1→B2→C1→C2），同等級再依字母；`count`＝依出現次數 | `level` |
| `--top` | 報告中列出的未知單詞數量 | `30` |
| `--no-definitions` | 不加入 WordNet 英文定義（詞形還原仍會使用） | 無 |
| `--no-estimated` | 只用 CEFR-J / Octanove 的人工等級，不使用推算等級 | 無 |
| `--lookup` | 查詢單詞等級後離開 | 無 |
| `--ocr` | OCR 模式：`auto`＝沒有文字層才 OCR、`force`＝PDF 一律 OCR、`off`＝關閉 | `auto` |
| `--ocr-dpi` | OCR 時 PDF 渲染解析度 | `200` |
| `--translate` | 把單詞翻譯成指定語言（`zh-TW`、`zh-CN`、`ja`、`ko`、`es`、`fr`…；只翻單詞） | 無 |
| `--translator` | 翻譯服務：`auto`＝先 Google，不回應時改用 MyMemory；`google`；`mymemory` | `auto` |
| `--translation-cache` | 翻譯快取資料夾 | `translation_cache` |
| `--dictionary` | 改用其他 CEFR 字典 CSV | 內建字典 |

## 輸出（預設在 `output/`）

| 檔案 | 用途 |
|------|------|
| `vocabulary_book.xlsx` | Excel 單詞簿（含「翻譯」欄與「等級統計」分頁） |
| `vocabulary_book.csv` | CSV 單詞簿，可作為 `--merge` 的合併檔 |
| `vocabulary_anki.tsv` | Anki 匯入檔（單詞／定義／例句／等級／詞性／翻譯） |
| `vocabulary_eudic.txt` | 欧路词典、有道等生詞本匯入檔（每行一詞） |
| `vocabulary_book.json` | JSON 格式 |
| `analysis_report.txt` | 完整分析報告（各等級分布 + 單詞簿 + 常見未知單詞） |

## 匯入字典／背單詞 App

- **Anki**：檔案 → 匯入 → 選擇 `vocabulary_anki.tsv`，分隔符選「Tab」，
  欄位對應「單詞、定義、例句、等級、詞性、翻譯」。
- **欧路词典（Eudic）**：學習 → 生詞本 → 匯入 → 選 `vocabulary_eudic.txt`（每行一個單詞）。
- **有道／其他**：多數 App 支援匯入每行一個單詞的 `.txt`，用 `vocabulary_eudic.txt` 即可。

## 等級判定規則

- 單詞先以小寫、去重音、原形比對；比不到時用 WordNet 做詞形還原後再比對。
- 一個單詞若同時出現在多個等級，以「較低」等級為主（CEFR 慣例），並在 `all_levels` 保留全部等級。
- 片語（如 `climate change`）會以 2–4 字連詞比對，與單詞分開列在單詞簿中。
- 主字典查不到的單詞，改用推算字典（Maximax67）。這些單詞在 Excel 的「推算等級」欄標為「推算」，
  在 Anki 檔與報告中等級後面加 `*`（例如 `C2*`），等級僅供參考。加 `--no-estimated` 可關閉。
- 網址、DOI、電子郵件會在掃描前移除，不會被當成單詞。

## 開發

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

重建 CEFR 字典：`python -m vocabulary_scanner.buildDictionary`（詳見 `data/SOURCES.md`）。

## 注意事項

- 舊版 Word `.doc` 與 Excel `.xls` 不直接支援，請先用 Word/Excel 另存成 `.docx`／`.xlsx`。
- 掃描圖片 PDF 會自動用 OCR（macOS）；解析度越高（`--ocr-dpi`）越準但越慢，頁數多時請耐心等待。
- 翻譯需連上網路；首次翻譯一批新單詞會較慢，之後走快取（`translation_cache/`）就快了。
- CEFR 等級為「近似」參考，同一個字在不同語境、不同詞性下等級可能不同。
