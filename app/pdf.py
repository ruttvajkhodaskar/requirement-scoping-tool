import io
import re

from pypdf import PdfReader


class PdfError(ValueError):
    """The PDF cannot be used. The message is safe to show to the user."""


def extract_pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        raise PdfError("The file is not a PDF.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise PdfError("The PDF is password protected.")
        pages = [(p.extract_text() or "") for p in reader.pages]
    except PdfError:
        raise
    except Exception as e:
        raise PdfError(f"The PDF could not be read ({type(e).__name__}).") from e

    text = "\n".join(pages).strip()
    if not text:
        raise PdfError("No text found. This looks like a scanned PDF, which needs OCR first.")
    # Join lines that were wrapped in the middle of a sentence.
    return re.sub(r"(?<![.!?:;])\n(?!\n)", " ", text)
