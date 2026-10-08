import os
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from app.core.config import settings

def generate_pdf_certificate(recipient_name: str, event_name: str, certificate_title: str, event_date: str, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    c = canvas.Canvas(output_path, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    c.setLineWidth(5)
    c.setStrokeColor(colors.darkblue)
    c.rect(0.5 * inch, 0.5 * inch, width - 1 * inch, height - 1 * inch)
    
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width / 2.0, height - 2.5 * inch, certificate_title)
    
    c.setFont("Helvetica", 18)
    c.drawCentredString(width / 2.0, height - 3.5 * inch, "This is proudly presented to")
    
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2.0, height - 4.5 * inch, recipient_name)
    
    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2.0, height - 5.5 * inch, f"For successfully completing the event:")
    
    c.setFont("Helvetica-Oblique", 20)
    c.drawCentredString(width / 2.0, height - 6.2 * inch, event_name)
    
    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2.0, height - 7.0 * inch, f"Date: {event_date}")
    
    c.showPage()
    c.save()
    return output_path
