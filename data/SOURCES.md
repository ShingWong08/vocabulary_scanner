# CEFR 字典資料來源

程式使用兩份字典，都放在 `src/vocabulary_scanner/data/`：

| 字典 | 內容 | 來源 |
|---|---|---|
| `cefr_words.csv`（主字典） | 約 1 萬筆人工標注等級（A1–C2） | CEFR-J 1.6 + Octanove C1/C2 1.0 |
| `cefr_words_estimated.csv`（推算字典） | 約 6.8 萬個主字典沒有的單詞，等級為推算值 | Maximax67 Words-CEFR-Dataset |

掃描時先查主字典；**只有主字典查不到**時才用推算字典，這些單詞在輸出檔中標為「推算」（Excel）或 `*`（Anki、報告）。
不想使用推算等級時，掃描加上 `--no-estimated`。

## 1. CEFR-J Wordlist (ver 1.6)

- 涵蓋 A1、A2、B1、B2
- Compiled by Yukio Tono, Tokyo University of Foreign Studies (TUFS)
- 取自 http://www.cefr-j.org/download.html （`CEFRJ_wordlist_ver1.6.zip`，2020-03-24 更新版，下載於 2026-11-18）
- 原始檔：`data/cefrj-vocabulary-profile-1.6.csv`，由 zip 內試算表的 `ALL` 工作表轉換而成
  （欄位：headword, pos, CEFR, CoreInventory 1, CoreInventory 2, Threshold）。原始 zip 未保留，需要時可從官網重新下載。
- 與 1.5 版（[openlanguageprofiles/olp-en-cefrj](https://github.com/openlanguageprofiles/olp-en-cefrj) 上的版本）的差異：
  補上英式／異體拼法（afterwards、storey、emphasise、tonne 等）並新增 being、having。
- 授權：可免費使用於研究與商業用途，惟須適當引用；版權屬東京外國語大學 Tono Laboratory。

## 2. Octanove Vocabulary Profile C1/C2 (ver 1.0)

- 涵蓋 C1、C2，由 Octanove Labs 製作，取自 [openlanguageprofiles/olp-en-cefrj](https://github.com/openlanguageprofiles/olp-en-cefrj)（截至 2026-11-18 仍為最新版）
- 原始檔：`data/octanove-vocabulary-profile-c1c2-1.0.csv`
- 授權：Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)

## 3. Maximax67 Words-CEFR-Dataset（推算等級）

- 取自 [Maximax67/Words-CEFR-Dataset](https://github.com/Maximax67/Words-CEFR-Dataset)（`csv/` 資料夾，下載於 2026-11-18）
- 原始檔（約 13 MB）未保留在專案中。需要重建推算字典時，把 `words.csv`、`word_pos.csv`、`pos_tags.csv`
  從 https://github.com/Maximax67/Words-CEFR-Dataset/tree/main/csv 下載到 `data/maximax67/`。
- 等級是以 CEFR-J 為基礎，再依 Google Books 詞頻、詞形與詞幹**推算**出來的（1.0＝A1 … 6.0＝C2），不是人工標注，準確度較低。
- 建立推算字典時的處理：
  - 去掉主字典已有的單詞
  - 去掉專有名詞、數字、外來字、符號（詞性標記 NNP、NNPS、CD、FW、LS、POS、SYM）
  - 去掉少於 3 個字母或含數字、符號的字
  - 只保留 WordNet 中當作一般單詞的字（去掉只當人名、地名的字）
  - 同一單詞有多個詞性時取最低等級，四捨五入到最接近的 CEFR 等級
- 授權：MIT License，Copyright (c) 2024 Belikov Maxim（全文見 `src/vocabulary_scanner/data/THIRD_PARTY_NOTICES.md`，會隨套件一起發佈）

## 引用方式（建議）

> The CEFR-J Wordlist Version 1.6. Compiled by Yukio Tono, Tokyo University of Foreign Studies.
> Octanove Vocabulary Profile C1/C2 (ver 1.0), Octanove Labs, CC BY-SA 4.0.
> Words CEFR Dataset by Belikov Maxim (Maximax67), MIT License.

## 重新產生

在專案資料夾執行（需要已下載 WordNet）：

```bash
python -m vocabulary_scanner.buildDictionary
```

預設讀取 `data/` 內的 CEFR-J 1.6、Octanove 與 `data/maximax67/`，寫入兩份字典。
`data/maximax67/` 沒有原始檔時，只重建主字典，保留現有的推算字典；只想重建主字典也可以加 `--no-estimated`。

說明：當一個單詞同時出現在多個等級時，程式取「較低」等級作為主要等級
（符合 CEFR「該詞最早於此等級習得」的慣例），同時在 `all_levels` 保留全部等級。
