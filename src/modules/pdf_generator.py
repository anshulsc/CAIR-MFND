# src/modules/pdf_generator.py

import json
import re
from pathlib import Path
from PIL import Image
from fpdf import FPDF, XPos, YPos
from markdown2 import Markdown
from datetime import datetime
from src.config import BASE_DIR, PROCESSED_DIR, RESULTS_DIR


COLOR_PRIMARY = (33, 37, 41)
COLOR_SECONDARY = (108, 117, 125)
COLOR_TRUE = (40, 167, 69)
COLOR_FAKE = (220, 53, 69)
COLOR_BORDER = (233, 236, 239)
COLOR_HIGHLIGHT = (248, 249, 250)
COLOR_NEUTRAL = (13, 110, 253)


ASSETS_DIR = BASE_DIR /  "assets"
FONT_REGULAR_PATH = str(ASSETS_DIR / "fonts" / "DejaVuSans.ttf")
FONT_BOLD_PATH = str(ASSETS_DIR / "fonts" / "DejaVuSans-Bold.ttf")

def _parse_final_response(response_text):
    verdict_match = re.search(r"\*\*Final Classification\*\*:\s*(\w+)", response_text, re.IGNORECASE)
    verdict = verdict_match.group(1).upper() if verdict_match else "UNCERTAIN"
    reasoning = re.sub(r"\*\*Final Classification\*\*:\s*\w+\n*", "", response_text, flags=re.IGNORECASE).strip()
    return verdict, reasoning

def _render_styled_line(pdf: FPDF, line: str):
    pdf.set_font(pdf.font_family, '', 10)
    pdf.set_text_color(*COLOR_PRIMARY)
    
    parts = re.split(r'(\*\*.*?\*\*|`.*?`)', line)
    
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            pdf.set_font(pdf.font_family, 'B', 10)
            clean_part = part[2:-2]
            if 'Mismatch' in clean_part: pdf.set_text_color(*COLOR_FAKE)
            elif 'Aligned' in clean_part: pdf.set_text_color(*COLOR_TRUE)
            pdf.write(6, clean_part)
            pdf.set_font(pdf.font_family, '', 10)
            pdf.set_text_color(*COLOR_PRIMARY)
        elif part.startswith('`') and part.endswith('`'):
            clean_part = part[1:-1]
            pdf.set_fill_color(*COLOR_HIGHLIGHT)
            pdf.cell(pdf.get_string_width(clean_part) + 2, 6, clean_part, fill=True)
        else:
            clean_part = part.replace('*', '')
            pdf.write(6, clean_part)
    pdf.ln(6)

def _render_markdown_block(pdf: FPDF, text: str):
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line: continue

        if line.startswith('###'):
            pdf.ln(6); pdf.set_font(pdf.font_family, 'B', 11); pdf.set_text_color(*COLOR_PRIMARY)
            pdf.multi_cell(0, 6, line.replace('###', '').strip()); pdf.ln(2)
        elif line.startswith('---'):
            pdf.ln(2); pdf.line(pdf.get_x(), pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y()); pdf.ln(4)
        elif line.startswith('Arguments FOR') or line.startswith('Arguments AGAINST'):
            pdf.ln(6); pdf.set_font(pdf.font_family, 'B', 10); pdf.set_text_color(*COLOR_NEUTRAL)
            pdf.multi_cell(0, 6, line); pdf.ln(1)
        elif line.startswith('*') or line.startswith('•'):
            pdf.set_x(pdf.l_margin + 5)
            pdf.set_font(pdf.font_family, 'B', 10); pdf.cell(5, 6, "•")
            _render_styled_line(pdf, line[1:].strip())
        elif re.match(r'^\d+\.\s', line):
            pdf.set_x(pdf.l_margin + 5)
            num = re.match(r'^(\d+)\.', line).group(1)
            pdf.set_font(pdf.font_family, 'B', 10); pdf.cell(5, 6, f"{num}.")
            _render_styled_line(pdf, re.sub(r'^\d+\.\s*', '', line))
        else:
            _render_styled_line(pdf, line)

markdowner = Markdown()

class PDFReport(FPDF):

    def __init__(self, query_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_id = query_id
        self.set_auto_page_break(auto=True, margin=20)
        self.alias_nb_pages()
        self.generation_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        try:
            self.add_font("DejaVu", "", FONT_REGULAR_PATH)
            self.add_font("DejaVu", "B", FONT_BOLD_PATH)
            self.font_family = "DejaVu"
        except RuntimeError:
            print(f"CRITICAL: Font files not found. Please run the wget commands to download them to {ASSETS_DIR / 'fonts'}")
            raise

    def header(self):
        self.set_font(self.font_family, "B", 18)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 10, "Fake News Analysis Report", border=False, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font(self.font_family, "", 10)
        self.set_text_color(*COLOR_SECONDARY)
        self.cell(0, 10, f"Query ID: {self.query_id}", border="B", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_family, "", 8)
        self.set_text_color(*COLOR_SECONDARY)
        self.cell(0, 10, f"Report generated on: {self.generation_timestamp}", 0, 0, "L")
        self.cell(0, 10, f"Page {self.page_no()} / {{nb}}", 0, 0, "R")

    def add_section_title(self, title, icon=""):
        self.set_font(self.font_family, "B", 14)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 10, f"{icon} {title}".strip(), border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(10)

    def _add_media_block(self, title, image_path, caption):
        """Helper to add a full-width, vertically stacked image and caption block."""
        self.set_font(self.font_family, 'B', 12)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 8, title, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(4)

        page_width = self.w - self.l_margin - self.r_margin
        img_box_h = 50
        display_h = img_box_h 

        try:
            if not image_path or not Path(image_path).exists():
                raise FileNotFoundError("Image path is invalid or None.")

            with Image.open(image_path) as img:
                img_w, img_h = img.size
                aspect_ratio = img_w / img_h
            
            display_w = page_width
            calculated_h = display_w / aspect_ratio
            if calculated_h > img_box_h:
                display_h = img_box_h
                display_w = display_h * aspect_ratio
            else:
                display_h = calculated_h
            
            x_pos = self.l_margin + (page_width - display_w) / 2
            self.image(image_path, x=x_pos, w=display_w, h=display_h)

        except Exception as e:
            print(f"WARN: Could not load image '{image_path}'. Reason: {e}")
            placeholder_x = self.l_margin + (page_width - 100) / 2
            self.set_fill_color(*COLOR_HIGHLIGHT)
            self.rect(placeholder_x, self.get_y(), 100, img_box_h, 'F')
            self.set_y(self.get_y() + img_box_h / 2 - 5)
            self.set_x(placeholder_x)
            self.cell(100, 10, "[Image not found]", align='C')

        self.ln(display_h - 38)
        
        self.set_font(self.font_family, '', 10)
        self.set_text_color(*COLOR_SECONDARY)
        self.multi_cell(0, 5, f'"{caption}"', align='C')
        self.ln(10)

    def add_summary_page(self, verdict_response, q_img, q_cap, e_img, e_cap):
        self.add_page()
        verdict, _ = _parse_final_response(verdict_response)
        banner_color, verdict_text = (COLOR_FAKE, "VERDICT: FAKE NEWS") if "FAKE" in verdict else (COLOR_TRUE, "VERDICT: TRUE NEWS")
        
        self.set_font(self.font_family, "B", 20)
        self.set_fill_color(*banner_color); self.set_text_color(255, 255, 255)
        self.cell(0, 15, verdict_text, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(12)

        self._add_media_block("Query News Sample", q_img, q_cap)
        self._add_media_block("Top Visual Evidence", e_img, e_cap)
        
    def write_markdown_cell(self, text):

        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line: continue 

            if line.startswith('**STEP') or line.startswith('Okay, let\'s analyze'):
                self.ln(8) 
                self.set_font(self.font_family, 'B', 11)
                self.set_text_color(*COLOR_PRIMARY)
                line = re.sub(r'\*\*(.*?)\*\*', r'\1', line) 
                self.multi_cell(0, 6, line)
                self.ln(2)
            elif line.startswith('Arguments FOR') or line.startswith('Arguments AGAINST'):
                self.ln(6)
                self.set_font(self.font_family, 'B', 10)
                self.set_text_color(*COLOR_NEUTRAL)
                self.multi_cell(0, 6, line)
                self.ln(1)
            
            elif line.startswith('•') or line.startswith('* ') or re.match(r'^\d+\.', line):
                self.set_x(self.l_margin + 5) # Indent bullet points
                self.set_font(self.font_family, '', 10)
                self.set_text_color(*COLOR_PRIMARY)
                
                if 'Mismatch' in line: self.set_text_color(*COLOR_FAKE)
                elif 'Aligned' in line: self.set_text_color(*COLOR_TRUE)
                
                self.multi_cell(0, 6, line)
                self.ln(1)
            
            else:
                self.set_font(self.font_family, '', 10)
                self.set_text_color(*COLOR_PRIMARY)
                
                if '**' in line:
                    parts = re.split(r'(\*\*.*?\*\*)', line)
                    for part in parts:
                        if part.startswith('**'):
                            self.set_font(self.font_family, 'B', 10)
                            self.write(6, part.replace('**', ''))
                            self.set_font(self.font_family, '', 10)
                        else:
                            self.write(6, part)
                    self.ln(6)
                else:
                    self.multi_cell(0, 6, line)
                    self.ln(2)
                    
    def add_reasoning_page(self, title, markdown_text, icon):
        self.add_page()
        self.add_section_title(title, icon)
        _render_markdown_block(self, markdown_text)
            
    def add_txt_txt_analysis_page(self, txt_txt_results):
        self.add_page()
        self.add_section_title("Text vs. Text Factual Consistency Analysis", icon="📝")

        for i, result_str in enumerate(txt_txt_results):
            if self.get_y() > self.h - 60:
                self.add_page()
                self.add_section_title("Text vs. Text Analysis (cont.)", icon="📝")

            self.set_font(self.font_family, "B", 11); self.set_fill_color(*COLOR_HIGHLIGHT)
            self.cell(0, 9, f"Evidence Snippet #{i+1}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(5)

            try:
                data = json.loads(re.sub(r"```json|```", "", result_str).strip())
                score = data.get("FactualAlignmentScore", "N/A")
                rationale = data.get("rationale", "No rationale provided.")
                
                self.set_font(self.font_family, "B", 9); self.cell(35, 6, "Factual Score:", align='L')
                self.set_font(self.font_family, "", 9); self.cell(0, 6, str(score), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.set_font(self.font_family, "B", 9); self.cell(35, 6, "Rationale:", align='L')
                self.set_x(self.l_margin + 35); self.set_font(self.font_family, "", 9)
                self.multi_cell(0, 6, rationale)
                self.ln(12)
                
            except (json.JSONDecodeError, AttributeError):
                self.set_font(self.font_family, "", 9); self.set_text_color(*COLOR_FAKE)
                self.multi_cell(0, 5, "[Could not parse this text-text result]"); self.set_text_color(*COLOR_PRIMARY)
                self.ln(12)

def create_report_pdf(metadata_path: Path, results_path: Path) -> Path:
    with open(metadata_path, 'r', encoding='utf-8') as f: metadata = json.load(f)
    with open(results_path, 'r', encoding='utf-8') as f: results = json.load(f)

    query_id = metadata['query_id']
    
    # Resolve relative paths
    base_dir = metadata_path.parent
    query_img_path = base_dir / metadata['query_image_path']
    
    query_caption_path = base_dir / metadata['query_caption_path']
    with open(query_caption_path, 'r', encoding='utf-8') as f: query_caption = f.read().strip()
    
    best_evidence_path = base_dir / "best_evidence.jpg"
    best_evidence_caption = "No text evidence found or evidence file is missing."
    if metadata.get('evidences') and metadata['evidences']:
        from src.config import BASE_DIR
        cap_rel_path = metadata['evidences'][0]['caption_path']
        cap_path = BASE_DIR / cap_rel_path
        if cap_path.exists(): best_evidence_caption = cap_path.read_text(encoding='utf-8').strip()

    pdf = PDFReport(query_id)
    stage2 = results['stage2_outputs']
    _, final_reasoning = _parse_final_response(stage2['final_response'])
    
    pdf.add_summary_page(
        stage2['final_response'],
        query_img_path, query_caption,
        str(best_evidence_path) if best_evidence_path.exists() else None,
        best_evidence_caption
    )
    
    pdf.add_reasoning_page("Final Unified Reasoning", final_reasoning, "🧠")
    pdf.add_reasoning_page("Image vs. Text Analysis (Query)", stage2['img_txt_result'], "🖼️")
    pdf.add_reasoning_page("Query Image vs. Evidence Image Analysis", stage2['qimg_eimg_result'], "🔍")
    pdf.add_txt_txt_analysis_page(stage2['txt_txt_results'])

    output_dir = RESULTS_DIR / query_id
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "analysis_report.pdf"
    pdf.output(output_path)
    
    print(f"INFO: Professional PDF report generated successfully at: {output_path}")
    return output_path

if __name__ == "__main__":
    print("--- Running Standalone Professional PDF Generator Test ---")
    test_query_id = "8"
    
    test_metadata_path = PROCESSED_DIR / test_query_id / "evidence_metadata.json"
    test_results_path = PROCESSED_DIR / test_query_id / "inference_results.json"

    if test_metadata_path.exists() and test_results_path.exists():
        create_report_pdf(test_metadata_path, test_results_path)
        print(f"\nSUCCESS: PDF for '{test_query_id}' has been regenerated with the font error fix.")
    else:
        print(f"\nERROR: Input files not found for '{test_query_id}'.")