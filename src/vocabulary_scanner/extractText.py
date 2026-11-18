import html
import os
import re

from vocabulary_scanner import visionOCR
from vocabulary_scanner.chatColor import ChatColor


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "word",
    ".xlsx": "excel",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tif": "image",
    ".tiff": "image",
    ".bmp": "image",
    ".txt": "text",
    ".csv": "text",
    ".tsv": "text",
    ".md": "text",
    ".markdown": "text",
    ".html": "html",
    ".htm": "html",
}

OCR_MODES = ["auto", "force", "off"]

# latin-1 accepts any bytes, so it must be the last encoding to try.
# English letters are the same in all three, which is all the scanner needs.
TEXT_ENCODINGS = ["utf-8-sig", "cp1252", "latin-1"]

# A PDF with less text than this is treated as a scanned PDF (no text layer)
MIN_PDF_TEXT_LENGTH = 40

HIDDEN_HTML_PATTERN = re.compile(r"<(script|style)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def collectInputFiles(inputs: list[str]) -> list[str]:

    """
    Expand files and folders into a list of supported files. Folders are scanned recursively, in name order.
    Paths that do not exist are reported and skipped.
    """

    files = []

    for eachInput in inputs:
        if os.path.isdir(eachInput):
            for root, folderNames, fileNames in os.walk(eachInput):
                folderNames.sort()

                for eachName in sorted(fileNames):
                    if isSupportedFile(eachName):
                        files.append(os.path.join(root, eachName))

        elif os.path.isfile(eachInput):
            files.append(eachInput)

        else:
            print(ChatColor.paint(f"Not found: {eachInput}", ChatColor.ORANGE))

    return files


def isSupportedFile(filePath: str) -> bool:
    extension = os.path.splitext(filePath)[1].lower()
    return extension in SUPPORTED_EXTENSIONS


def extractText(filePath: str, ocrMode: str = "auto", ocrDPI: int = 200) -> str:

    """
    Read the text of a PDF, Word, Excel, image, HTML or plain text file.
    Parameters:
        Mandatory:
            - filePath (str): Path to the file.
        Optional:
            - ocrMode (str): "auto" = OCR only PDFs without a text layer, "force" = OCR every PDF, "off" = never OCR.
            - ocrDPI (int): Resolution used to render PDF pages for OCR.
        Default:
            - ocrMode: "auto"
            - ocrDPI: 200
    Returns:
        str: The text of the file, or "" if nothing could be read.
    """

    extension = os.path.splitext(filePath)[1].lower()
    fileType = SUPPORTED_EXTENSIONS.get(extension)

    if fileType == "pdf":
        return readPDFFile(filePath, ocrMode, ocrDPI)

    if fileType == "word":
        return readWordFile(filePath)

    if fileType == "excel":
        return readExcelFile(filePath)

    if fileType == "image":
        return readImageFile(filePath, ocrMode)

    if fileType == "html":
        return readHTMLFile(filePath)

    if fileType == "text":
        return readTextFile(filePath)

    print(ChatColor.paint(f"Unsupported file type, skipped: {filePath}", ChatColor.ORANGE))
    return ""


def readTextFile(filePath: str) -> str:

    """
    Read a plain text file, trying UTF-8 first, then Windows-1252, then Latin-1.
    """

    for eachEncoding in TEXT_ENCODINGS:
        try:
            with open(filePath, encoding=eachEncoding) as textFile:
                return textFile.read()
        except UnicodeError:
            continue

    return ""


def readHTMLFile(filePath: str) -> str:

    """
    Read an HTML file and keep only its visible text (no tags, scripts or styles).
    """

    text = readTextFile(filePath)
    text = HIDDEN_HTML_PATTERN.sub(" ", text)
    text = HTML_TAG_PATTERN.sub(" ", text)
    return html.unescape(text)


def readPDFFile(filePath: str, ocrMode: str = "auto", ocrDPI: int = 200) -> str:

    """
    Read the text layer of a PDF with pdfplumber (or pypdf as a fallback).
    Scanned PDFs without a text layer are read with OCR (macOS only).
    """

    text = ""

    if ocrMode != "force":
        text = readPDFTextLayer(filePath)

    if ocrMode == "off":
        return text

    needsOCR = ocrMode == "force" or len(text.strip()) < MIN_PDF_TEXT_LENGTH
    if not needsOCR:
        return text

    if not visionOCR.isOCRAvailable():
        if text.strip() == "":
            print(ChatColor.paint("This PDF has no text layer, and OCR only works on macOS.", ChatColor.ORANGE))
        return text

    ocrText = visionOCR.ocrPDF(filePath, dpi=ocrDPI)
    if ocrText.strip() != "":
        return ocrText

    return text


def readPDFTextLayer(filePath: str) -> str:
    text = ""

    try:
        import pdfplumber

        with pdfplumber.open(filePath) as pdf:
            pageTexts = [eachPage.extract_text() or "" for eachPage in pdf.pages]
        text = "\n".join(pageTexts)
    except ImportError:
        print(ChatColor.paint("pdfplumber is not installed, trying pypdf...", ChatColor.ORANGE))
    except Exception as error:
        print(ChatColor.paint(f"pdfplumber could not read the PDF ({error}), trying pypdf...", ChatColor.ORANGE))

    if text.strip() != "":
        return text

    try:
        from pypdf import PdfReader

        reader = PdfReader(filePath)
        pageTexts = [eachPage.extract_text() or "" for eachPage in reader.pages]
        text = "\n".join(pageTexts)
    except ImportError:
        print(ChatColor.paint("pypdf is not installed. Run: pip install -e .", ChatColor.ORANGE))
    except Exception as error:
        print(ChatColor.paint(f"Could not read the PDF: {error}", ChatColor.RED))

    return text


def readWordFile(filePath: str) -> str:

    """
    Read the paragraphs and tables of a Word (.docx) file.
    """

    try:
        import docx
    except ImportError:
        print(ChatColor.paint("python-docx is not installed. Run: pip install -e .", ChatColor.ORANGE))
        return ""

    try:
        document = docx.Document(filePath)
    except Exception as error:
        print(ChatColor.paint(f"Could not read the Word file: {error}", ChatColor.RED))
        return ""

    parts = [eachParagraph.text for eachParagraph in document.paragraphs]

    for eachTable in document.tables:
        for eachRow in eachTable.rows:
            parts.append(" ".join(eachCell.text for eachCell in eachRow.cells))

    return "\n".join(parts)


def readExcelFile(filePath: str) -> str:

    """
    Read every non-empty cell of every sheet in an Excel (.xlsx) file, one row per line.
    """

    try:
        import openpyxl
    except ImportError:
        print(ChatColor.paint("openpyxl is not installed. Run: pip install -e .", ChatColor.ORANGE))
        return ""

    try:
        workbook = openpyxl.load_workbook(filePath, data_only=True, read_only=True)
    except Exception as error:
        print(ChatColor.paint(f"Could not read the Excel file: {error}", ChatColor.RED))
        return ""

    lines = []

    try:
        for eachSheet in workbook.worksheets:
            for eachRow in eachSheet.iter_rows(values_only=True):
                cells = [str(eachCell) for eachCell in eachRow if eachCell is not None]
                if len(cells) > 0:
                    lines.append(" ".join(cells))
    finally:
        workbook.close()

    return "\n".join(lines)


def readImageFile(filePath: str, ocrMode: str = "auto") -> str:

    """
    Read the text in an image with OCR (macOS only).
    """

    if ocrMode == "off":
        return ""

    if not visionOCR.isOCRAvailable():
        print(ChatColor.paint("Images need OCR, which only works on macOS.", ChatColor.ORANGE))
        return ""

    return visionOCR.ocrImage(filePath)


if __name__ == "__main__":
    for eachFile in collectInputFiles(["sample"]):
        print(eachFile, len(extractText(eachFile)))
