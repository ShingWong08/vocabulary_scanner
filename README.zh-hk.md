# 英文文件 CEFR 單詞等級掃描工具

**中文** | [English](README.md)

## 簡介

這是一個命令列工具，可以掃描 PDF、Word、Excel、圖片和純文字檔，分析每個英文單詞的 CEFR 等級（A1–C2），
並自動把 **B2 到 C2** 的高級單詞和片語整理成單詞簿，附上英文定義和原文例句。
單詞簿可以匯出成 Excel、CSV、Anki、欧路词典等格式，方便匯入字典或背單詞 App。

> [!NOTE]
> 掃描圖片 PDF 的 OCR 功能只支援 macOS。Windows 會略過圖片檔和沒有文字層的 PDF，其他格式不受影響。

---

## 需求

- Python 3.10 以上
- pip
- （選用）macOS 的 Xcode 命令列工具：OCR 需要
- （選用）網路連線：翻譯需要

---

## 安裝

> [!NOTE]
> 也可以直接從 PyPI 安裝：`python -m pip install vocabulary-scanner`，
> macOS 要使用 OCR 時改裝 `"vocabulary-scanner[ocr]"`。安裝完同樣要執行下面第 3 步下載 WordNet。

1. **建立並啟用虛擬環境：**

    Windows（PowerShell）

    ```powershell
    python -m venv env
    .\env\Scripts\Activate.ps1
    ```

    macOS / Linux

    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

2. **安裝套件：**

    Windows

    ```powershell
    python -m pip install -e .
    ```

    macOS（包含 OCR）

    ```bash
    python3 -m pip install -e ".[ocr]"
    ```

3. **下載 WordNet 資料（只需一次）：**

    ```
    python -m nltk.downloader wordnet omw-1.4
    ```

    WordNet 用於英文定義和詞形還原。沒下載的話，程式第一次執行時會自動嘗試下載；
    就算下載失敗，程式仍然可以執行，只是會跳過詞形還原和英文定義。

4. **開始掃描：**

    ```
    vocab-scanner sample/
    ```

    執行後，結果會寫到目前資料夾的 `output/`。

之後每次開新的終端機，都要先啟用虛擬環境（第 1 步的第二行）。

---

## 使用方法

安裝後會有 `vocab-scanner` 指令（也可以用 `python -m vocabulary_scanner`，效果相同）。

> [!TIP]
> 路徑有空白時必須加引號，手動輸入很容易出錯。可以先輸入 `vocab-scanner`（**結尾留一個空格**），
> 再把檔案或資料夾從檔案總管／Finder 拖進終端機，路徑會自動貼上，然後按 Enter。

```bash
# 掃描整個資料夾
vocab-scanner sample/

# 掃描多個檔案
vocab-scanner report.pdf notes.docx data.xlsx

# 輸出到另一個資料夾，避免覆蓋上一次的結果
vocab-scanner essay.docx --out-dir output/essay

# 合併進既有單詞簿（累加次數、保留來源）
vocab-scanner new_docs/ --merge output/vocabulary_book.csv

# 只查詢某個單詞的等級
vocab-scanner --lookup ambiguous

# 把單詞翻譯成繁體中文（只翻單詞，不翻定義）
vocab-scanner sample/ --translate zh-TW

# 語言名稱或代碼都可以，例如 zh-CN、ja、ko、es、fr
vocab-scanner sample/ --translate 日文

# 強制所有 PDF 都用 OCR（macOS，通常不需要）／完全關閉 OCR
vocab-scanner scans/ --ocr force
vocab-scanner scans/ --ocr off
```

---

## 參數

所有參數都是選填的。

| 參數 | 說明 | 預設 |
|------|------|------|
| `inputs` | 檔案或資料夾（可多個） | 無 |
| `--out-dir` | 輸出資料夾 | `output` |
| `--min-level` | 單詞簿最低等級 | `B2` |
| `--max-level` | 單詞簿最高等級 | `C2` |
| `--merge` | 合併進既有 `vocabulary_book.csv` | 無 |
| `--sort` | `level`＝先依等級（A1→C2），同等級再依字母；`count`＝依出現次數 | `level` |
| `--top` | 報告中列出的未知單詞數量 | `30` |
| `--no-definitions` | 不加入 WordNet 英文定義（詞形還原仍會使用） | 無 |
| `--no-estimated` | 只用 CEFR-J / Octanove 的人工等級，不使用推算等級 | 無 |
| `--lookup` | 查詢單詞等級後離開 | 無 |
| `--ocr` | `auto`＝沒有文字層才 OCR；`force`＝PDF 一律 OCR；`off`＝關閉 | `auto` |
| `--ocr-dpi` | OCR 時 PDF 渲染解析度 | `200` |
| `--translate` | 把單詞翻譯成指定語言（`zh-TW`、`zh-CN`、`ja`、`ko`、`es`、`fr`…） | 無 |
| `--translator` | `auto`＝先 Google，不回應時改用 MyMemory；`google`；`mymemory` | `auto` |
| `--translation-cache` | 翻譯快取資料夾 | `translation_cache` |
| `--dictionary` | 改用其他 CEFR 字典 CSV | 內建字典 |

---

## 功能

- 支援 PDF（.pdf）、Word（.docx）、Excel（.xlsx）、圖片（.png/.jpg/.tiff）和純文字（.txt/.csv/.md/.html）
- 支援單一檔案、多個檔案或整個資料夾（遞迴掃描）
- 自動偵測沒有文字層的 PDF，改用 Apple Vision OCR 認字（僅 macOS，不需要 Tesseract）
- 內建 CEFR 字典：約 1 萬筆人工標注詞條（CEFR-J 1.6 + Octanove），
  另有約 6.8 萬個單詞的推算等級（Maximax67），補足字典沒收錄的字
- 詞形還原（run/runs/ran → run）和英文定義（WordNet，可離線使用）
- 片語比對（如 `climate change`），和單詞分開列出
- 可選翻譯：Google 翻譯，被擋時自動改用 MyMemory，結果會快取
- 匯出 Excel、CSV、Anki、欧路词典、JSON 和分析報告

---

## 輸出檔案

結果預設寫到 `output/`：

| 檔案 | 用途 |
|------|------|
| `vocabulary_book.xlsx` | Excel 單詞簿（含「翻譯」欄和「等級統計」分頁） |
| `vocabulary_book.csv` | CSV 單詞簿，可作為 `--merge` 的合併檔 |
| `vocabulary_anki.tsv` | Anki 匯入檔（單詞／定義／例句／等級／詞性／翻譯） |
| `vocabulary_eudic.txt` | 欧路词典、有道等生詞本匯入檔（每行一詞） |
| `vocabulary_book.json` | JSON 格式 |
| `analysis_report.txt` | 完整分析報告（各等級分布 + 單詞簿 + 常見未知單詞） |

**匯入背單詞 App**

- **Anki**：檔案 → 匯入 → 選擇 `vocabulary_anki.tsv`，分隔符選「Tab」，欄位對應「單詞、定義、例句、等級、詞性、翻譯」。
- **欧路词典**：學習 → 生詞本 → 匯入 → 選擇 `vocabulary_eudic.txt`。
- **有道／其他**：多數 App 支援匯入每行一個單詞的 `.txt`，用 `vocabulary_eudic.txt` 即可。

---

## 專案結構

```
vocabulary_scanner/
├── pyproject.toml                   # 套件設定與相依套件
├── requirements.txt                 # 同樣的相依套件清單（pip install -r 用）
├── src/vocabulary_scanner/
│   ├── __init__.py                  # 命令列主程式 main()
│   ├── __main__.py                  # 讓 python -m vocabulary_scanner 可以執行
│   ├── chatColor.py                 # 終端機彩色輸出
│   ├── cefrDictionary.py            # CEFR 字典與等級查詢
│   ├── connectWordNet.py            # WordNet 詞形還原與英文定義
│   ├── translation.py               # 翻譯：快取、語言名稱、自動切換翻譯服務
│   ├── connectGoogleTranslate.py    # Google 翻譯
│   ├── connectMyMemory.py           # MyMemory 翻譯（Google 被擋時的備援）
│   ├── extractText.py               # 讀取 PDF / Word / Excel / HTML / 文字檔
│   ├── visionOCR.py                 # Apple Vision OCR（macOS）
│   ├── visionOCR.swift              # OCR 輔助程式原始碼
│   ├── scanText.py                  # 斷句、比對單詞與片語
│   ├── exportVocabularyBook.py      # 匯出 Excel / CSV / Anki / 欧路 / JSON / 報告
│   ├── buildDictionary.py           # 由原始詞表重建字典
│   └── data/
│       ├── cefr_words.csv           # CEFR 主字典（CEFR-J + Octanove）
│       ├── cefr_words_estimated.csv # 推算等級字典（Maximax67）
│       └── THIRD_PARTY_NOTICES.md   # 字典資料的來源與授權聲明
├── data/                            # 原始詞表與資料來源說明（SOURCES.md）
├── sample/                          # 範例檔案
└── tests/                           # pytest 測試
```

---

## 等級判定規則

- 單詞先以小寫、去重音後的原形比對；比對不到時，用 WordNet 做詞形還原後再比對。
- 一個單詞若同時出現在多個等級，以**較低**的等級為準（CEFR 慣例），並在 `all_levels` 保留全部等級。
- 片語以 2–4 個字的連詞比對。
- 主字典查不到的單詞改用推算字典。這些單詞在 Excel 的「推算等級」欄標為「推算」，
  在 Anki 檔和報告中等級後面加 `*`（例如 `C2*`），僅供參考。加 `--no-estimated` 可關閉。
- 網址、DOI、電子郵件會在掃描前移除，不會被當成單詞。

---

## 開發

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

重建 CEFR 字典：`python -m vocabulary_scanner.buildDictionary`（詳見 `data/SOURCES.md`）。

---

## 注意事項

- 舊版 Word `.doc` 和 Excel `.xls` 不直接支援，請先另存成 `.docx`／`.xlsx`。
- OCR 第一次使用時會自動把 `visionOCR.swift` 編譯到 `~/.cache/vocabulary_scanner/`，需要 `swiftc`
  （終端機執行 `xcode-select --install` 安裝）。解析度越高（`--ocr-dpi`）越準但越慢。
- 翻譯結果快取在 `translation_cache/`，之後同樣的單詞離線也能用；翻譯失敗的單詞不會中斷掃描，下次執行會自動重試。
- Google 翻譯偶爾會因為短時間大量請求而暫時封鎖（通常幾小時到一天後恢復）；
  MyMemory 每天約有 5,000 字元的免費額度。可以用 `--translator` 指定翻譯服務。
- CEFR 等級只是近似參考，同一個字在不同語境、不同詞性下的等級可能不同。
- 遇到問題時，請先確認 Python 版本是 3.10 以上、已啟用虛擬環境，再重新執行 `python -m pip install -e .`。
