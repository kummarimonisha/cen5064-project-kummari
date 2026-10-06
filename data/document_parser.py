import io
import PyPDF2
import docx

def extract_text_from_file(filename: str, content: bytes) -> str:
    """Extracts text from PDF or DOCX files."""
    extracted_text = ""

    if filename.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text + "\n"

    elif filename.endswith(".docx"):
        doc = docx.Document(io.BytesIO(content))
        for para in doc.paragraphs:
            extracted_text += para.text + "\n"

    return extracted_text.strip()
