try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF (fitz) not found. Please install it with: pip install PyMuPDF")
    raise ImportError("PyMuPDF is required for PDF processing")

import base64
from io import BytesIO
from PIL import Image
import tempfile
import os

def pdf_to_images_from_bytes(pdf_bytes):
    """Convertit un PDF (bytes) en liste de PIL.Image (pour Streamlit)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    images = pdf_to_images_from_path(tmp_path)
    os.unlink(tmp_path)
    return images

def pdf_to_images_from_path(pdf_path):
    """Convertit un PDF (chemin) en liste de PIL.Image."""
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img = Image.open(BytesIO(pix.tobytes("png")))
        images.append(img)
    doc.close()
    return images

def image_to_base64(image: Image.Image) -> str:
    """Convertit une PIL.Image en chaîne Base64."""
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=85, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()

def build_vision_payload(images, prompt_text):
    """
    Construit la liste message_content pour GPT-4 Vision : 
    un bloc texte suivi d'un bloc par image encodée.
    """
    contents = [{"type": "text", "text": prompt_text}]
    for img in images:
        b64 = image_to_base64(img)
        contents.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"}
        })
    return contents


