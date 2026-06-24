"""
PDF Renderer - Tao file PDF tu plan va screenshots
"""
import logging
import re
from pathlib import Path
from typing import Dict
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Import base_renderer without relative import
import sys
sys.path.insert(0, str(Path(__file__).parent))
from base_renderer import Renderer

logger = logging.getLogger(__name__)

class PDFRenderer(Renderer):
    """Renderer de tao file PDF"""
    
    def __init__(self, output_dir: Path):
        super().__init__(output_dir)
        self._register_fonts()
    
    def _register_fonts(self):
        """Dang ky font Unicode cho tieng Viet"""
        try:
            # Thu dang ky Arial Unicode MS (Windows)
            font_paths = [
                'C:/Windows/Fonts/arial.ttf',
                'C:/Windows/Fonts/arialuni.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
            ]
            
            for font_path in font_paths:
                if Path(font_path).exists():
                    pdfmetrics.registerFont(TTFont('ArialUnicode', font_path))
                    logger.info(f"  [PDFRenderer] Registered font: {font_path}")
                    return
            
            logger.warning("  [PDFRenderer] Khong tim thay font Unicode, dung font mac dinh")
        except Exception as e:
            logger.warning(f"  [PDFRenderer] Loi dang ky font: {e}")
    
    def render(self, plan: Dict, artifacts: Dict) -> str:
        """Tao file PDF tu plan va screenshots"""
        logger.info("  [PDFRenderer] Bat dau render PDF...")
        
        output_path = self.output_dir / f"{plan.get('name', 'tutorial')}.pdf"
        
        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles voi font Unicode
        try:
            font_name = 'ArialUnicode'
        except:
            font_name = 'Helvetica'
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=24,
            textColor='darkblue',
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=14,
            textColor='darkblue',
            spaceAfter=12,
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
        )
        
        caption_style = ParagraphStyle(
            'CustomCaption',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9,
            textColor='gray',
            alignment=TA_CENTER,
            fontStyle='italic',
        )
        
        # Tieu de chinh
        title = plan.get('title', 'Tutorial')
        story.append(Paragraph(title, title_style))
        
        # Mo ta
        intro = 'Tai lieu huong dan nay duoc tao tu dong boi WebReel AI Agent. Vui long lam theo tung buoc de hoan thanh tac vu.'
        story.append(Paragraph(f'<i>{intro}</i>', body_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Them tung buoc
        steps = plan.get('steps', [])
        screenshots = artifacts.get('screenshots', [])
        
        for i, step in enumerate(steps):
            # Lay narration va clean up
            narration = step.get('narration', f'Buoc {i+1}')
            
            # Remove [NARRATION:X] prefix
            narration = re.sub(r'\[NARRATION:\d+\]\s*', '', narration)
            
            # Escape HTML special chars
            narration = narration.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Tieu de buoc
            step_title = f'<b>Buoc {i+1}</b>'
            story.append(Paragraph(step_title, heading_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Mo ta chi tiet
            story.append(Paragraph(narration, body_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Them anh neu co
            if i < len(screenshots) and screenshots[i]:
                screenshot_path = screenshots[i]
                if Path(screenshot_path).exists():
                    try:
                        # Tinh toan kich thuoc anh de fit trang A4
                        img = Image(screenshot_path)
                        img_width = 5.5 * inch
                        aspect = img.imageHeight / float(img.imageWidth)
                        img_height = img_width * aspect
                        
                        # Gioi han chieu cao
                        if img_height > 4 * inch:
                            img_height = 4 * inch
                            img_width = img_height / aspect
                        
                        img.drawWidth = img_width
                        img.drawHeight = img_height
                        
                        story.append(img)
                        
                        # Caption
                        caption = f'Hinh {i+1}: Minh hoa buoc {i+1}'
                        story.append(Paragraph(caption, caption_style))
                        
                    except Exception as e:
                        logger.error(f"  [PDFRenderer] Loi chen anh: {e}")
            
            story.append(Spacer(1, 0.3*inch))
        
        # Footer
        footer_text = '<i>WebReel AI Agent - Tutorial Documentation</i>'
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(footer_text, caption_style))
        
        # Build PDF
        try:
            doc.build(story)
            logger.info(f"  [PDFRenderer] Da luu PDF: {output_path}")
        except Exception as e:
            logger.error(f"  [PDFRenderer] Loi build PDF: {e}")
            raise
        
        return str(output_path)
    
    @property
    def output_format(self) -> str:
        return "pdf"

