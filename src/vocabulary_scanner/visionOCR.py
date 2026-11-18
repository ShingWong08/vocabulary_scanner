import os
import shutil
import subprocess
import sys
import tempfile

from vocabulary_scanner.chatColor import ChatColor


PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_SWIFT_SOURCE = os.path.join(PACKAGE_DIR, "visionOCR.swift")
OCR_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "vocabulary_scanner")
OCR_BINARY = os.path.join(OCR_CACHE_DIR, "visionOCR")

POINTS_PER_INCH = 72


def isOCRAvailable() -> bool:

    """
    Return True when OCR can be used.
    OCR uses Apple's Vision framework, so it only works on macOS with Xcode Command Line Tools (swiftc).
    This check does not compile anything; getOCRBinary compiles on first use.
    """

    if sys.platform != "darwin":
        return False

    if os.path.exists(OCR_BINARY):
        return True

    return shutil.which("swiftc") is not None and os.path.exists(OCR_SWIFT_SOURCE)


def getOCRBinary() -> str | None:

    """
    Return the path of the compiled OCR helper, compiling visionOCR.swift the first time.
    Returns None when OCR is not available on this computer.
    """

    if not isOCRAvailable():
        return None

    if os.path.exists(OCR_BINARY):
        return OCR_BINARY

    os.makedirs(OCR_CACHE_DIR, exist_ok=True)
    moduleCache = os.path.join(tempfile.gettempdir(), "vocabulary_scanner_swift_cache")
    os.makedirs(moduleCache, exist_ok=True)

    print(ChatColor.paint("Compiling the OCR helper (first run only)...", ChatColor.BLUE))
    command = [shutil.which("swiftc"), "-O", "-module-cache-path", moduleCache, OCR_SWIFT_SOURCE, "-o", OCR_BINARY]

    try:
        subprocess.run(command, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        print(ChatColor.paint("Could not compile the OCR helper.", ChatColor.RED))
        return None

    if not os.path.exists(OCR_BINARY):
        return None

    return OCR_BINARY


def ocrImage(imagePath: str) -> str:

    """
    Read the text in one image file with OCR. Returns "" if OCR is not available.
    """

    binary = getOCRBinary()
    if binary is None:
        return ""

    process = subprocess.run([binary, imagePath], capture_output=True, text=True, encoding="utf-8")
    return process.stdout or ""


def ocrPDF(pdfPath: str, dpi: int = 200) -> str:

    """
    Render every page of a PDF to an image and read it with OCR.
    Parameters:
        Mandatory:
            - pdfPath (str): Path to the PDF file.
        Optional:
            - dpi (int): Rendering resolution. Higher is more accurate but slower.
        Default:
            - dpi: 200
    Returns:
        str: The text of all pages, or "" if OCR or pypdfium2 is not available.
    """

    if getOCRBinary() is None:
        return ""

    try:
        import pypdfium2
    except ImportError:
        print(ChatColor.paint("pypdfium2 is not installed. Run: pip install -e .[ocr]", ChatColor.ORANGE))
        return ""

    pageTexts = []

    with tempfile.TemporaryDirectory(prefix="vocabulary_scanner_ocr_") as tempDir:
        try:
            document = pypdfium2.PdfDocument(pdfPath)
        except Exception as error:
            print(ChatColor.paint(f"Could not open the PDF for OCR: {error}", ChatColor.RED))
            return ""

        try:
            for pageIndex in range(len(document)):
                imagePath = os.path.join(tempDir, f"page_{pageIndex + 1:04d}.png")

                try:
                    bitmap = document[pageIndex].render(scale=dpi / POINTS_PER_INCH)
                    bitmap.to_pil().save(imagePath)
                except Exception:
                    continue

                pageTexts.append(ocrImage(imagePath))
        finally:
            document.close()

    return "\n".join(pageTexts)


if __name__ == "__main__":
    print("OCR available:", isOCRAvailable())
