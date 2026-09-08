"""
🎯 Quiz PDF Report Generator - TEXTBOOK LAYOUT FIX (PART 1 OF 4)
"""

import json
import sqlite3
import logging
import re
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Tuple, Optional
import urllib.request  
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class QuizPDFGenerator:
    """Generate comprehensive PDF reports matching the textbook image layout"""
    
    def __init__(self, db_file: str = "quiz_bot.db"):
        self.db_file = db_file
        self.logger = logging.getLogger(__name__)
        self._register_fonts()


    # 🎯 PART 2 OF 4: Font setup aur database fetching logic (Class ke andar jodhein)

    def _register_fonts(self):
        """
        Download and safely register a solid Devanagari TrueType font
        """
        try:
            font_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
            hindi_font_path = os.path.join(font_dir, "NotoSansDevanagari-Regular.ttf")
            hindi_bold_path = os.path.join(font_dir, "NotoSansDevanagari-Bold.ttf")
            
            if not os.path.exists(hindi_font_path):
                self.logger.info("⏬ Downloading NotoSansDevanagari Font...")
                urllib.request.urlretrieve(
                    "https://github.com", 
                    hindi_font_path
                )
            if not os.path.exists(hindi_bold_path):
                urllib.request.urlretrieve(
                    "https://github.com", 
                    hindi_bold_path
                )

            pdfmetrics.registerFont(TTFont('HindiFont', hindi_font_path))
            pdfmetrics.registerFont(TTFont('HindiFont-Bold', hindi_bold_path))
            
            self.default_font = 'HindiFont'
            self.default_font_bold = 'HindiFont-Bold'
            
            # Core styles override
            styles = getSampleStyleSheet()
            styles['Normal'].fontName = 'HindiFont'
            styles['BodyText'].fontName = 'HindiFont'
            styles['Heading1'].fontName = 'HindiFont-Bold'
            styles['Heading2'].fontName = 'HindiFont-Bold'
            styles['Heading3'].fontName = 'HindiFont-Bold'
                
        except Exception as e:
            self.logger.warning(f"Font download fail, activating Helvetica fallback: {e}")
            self.default_font = 'Helvetica'
            self.default_font_bold = 'Helvetica-Bold'
            
    def _fetch_quiz_data(self, quiz_id: int) -> Tuple[str, str, int]:
        """Fetch quiz metadata from database safely"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT title, description FROM quizzes WHERE quiz_id = ?", (quiz_id,))
            row = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) FROM questions WHERE quiz_id = ?", (quiz_id,))
            count_row = cursor.fetchone()
            conn.close()
            
            title = row[0] if row and row[0] else "Untitled Quiz"
            desc = row[1] if row and row[1] else "No description provided"
            total_q = count_row[0] if count_row else 0
            return title, desc, total_q
        except Exception as e:
            self.logger.error(f"Error fetching quiz data: {e}")
            return "Unknown Quiz", "Error", 0


    # 🎯 PART 3 OF 4: Main builder, header aur leaderboard flow (Class ke andar jodhein)

    def generate_quiz_report_pdf(
        self, chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0
    ) -> Optional[BytesIO]:
        """Generate a comprehensive, crash-free PDF report of the quiz results"""
        try:
            pdf_buffer = BytesIO()
            quiz_title, quiz_desc, total_questions = self._fetch_quiz_data(quiz_id)
            questions_data = self._fetch_all_questions(quiz_id)
            
            doc = SimpleDocTemplate(
                pdf_buffer, pagesize=A4, rightMargin=0.4*inch, leftMargin=0.4*inch, 
                topMargin=0.5*inch, bottomMargin=0.5*inch, title="Quiz Report"
            )
            
            story = []
            story.extend(self._build_header(quiz_title, quiz_desc, total_questions))
            story.append(Spacer(1, 0.2*inch))
            story.extend(self._build_leaderboard(game_data, final_scores, negative_value))
            story.append(PageBreak())
            story.extend(self._build_questions_section(questions_data, game_data, final_scores))
            story.append(Spacer(1, 0.3*inch))
            story.extend(self._build_footer(quiz_title, len(final_scores)))
            
            doc.build(story)
            pdf_buffer.seek(0)
            return pdf_buffer
        except Exception as e:
            self.logger.error(f"❌ Error generating PDF layout: {e}", exc_info=True)
            return None

    def _build_header(self, quiz_title: str, quiz_desc: str, total_q: int) -> List:
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'], fontSize=20,
            textColor=colors.HexColor('#1f4788'), spaceAfter=12, alignment=TA_CENTER, fontName=self.default_font_bold
        )
        desc_style = ParagraphStyle(
            'CustomDesc', parent=styles['Normal'], fontSize=11,
            textColor=colors.HexColor('#555555'), spaceAfter=8, alignment=TA_LEFT, fontName=self.default_font
        )
        
        title = Paragraph(f"<b>{self._sanitize_text(quiz_title)}</b>", title_style)
        description = Paragraph(f"<b>Description:</b> {self._sanitize_text(quiz_desc)}", desc_style)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = Paragraph(f"<b>Total Questions:</b> {total_q} | <b>Generated:</b> {now}", desc_style)
        
        divider = Table([['']], colWidths=[7.7*inch])
        divider.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f0f7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f4788')),
        ]))
        return [title, Spacer(1, 0.1*inch), description, metadata, Spacer(1, 0.1*inch), divider]
    
    def _build_leaderboard(self, game_data: Dict, final_scores: Dict, negative_value: float) -> List:
        styles = getSampleStyleSheet()
        leaderboard_title = ParagraphStyle(
            'LeaderboardTitle', parent=styles['Heading2'], fontSize=15,
            textColor=colors.HexColor('#1f4788'), spaceAfter=10, fontName=self.default_font_bold
        )
        normal_text = ParagraphStyle('NormalText', parent=styles['Normal'], fontSize=10, fontName=self.default_font)
        bold_text = ParagraphStyle('BoldText', parent=styles['Normal'], fontSize=10, fontName=self.default_font_bold)
        
        sorted_scores = sorted(final_scores.items(), key=lambda x: (-x[1]["points"], x[1]["total_time"]))[:50]
        leaderboard_data = [[
            Paragraph("<b>Rank</b>", bold_text), Paragraph("<b>Player Name</b>", bold_text),
            Paragraph("<b>Right</b>", bold_text), Paragraph("<b>Wrong</b>", bold_text),
            Paragraph("<b>Time (s)</b>", bold_text), Paragraph("<b>Score</b>", bold_text)
        ]]
        
        for rank, (uid, meta) in enumerate(sorted_scores, 1):
            player_name = game_data.get("joined_users", {}).get(str(uid), game_data.get("joined_users", {}).get(int(uid), f"User {uid}"))
            player_name = self._sanitize_text(player_name)
            
            leaderboard_data.append([
                Paragraph(f"{rank}.", normal_text), 
                Paragraph(player_name[:25], normal_text),
                Paragraph(str(meta["score"]), normal_text), 
                Paragraph(str(meta["wrong"]), normal_text),
                Paragraph(f"{meta['total_time']:.1f}", normal_text), 
                Paragraph(f"<b>{meta['points']:.2f}</b>", normal_text)
            ])
        
        neg_info = f"Negative Marking: -{negative_value}/wrong"
        leaderboard_data.append([Paragraph("", normal_text), Paragraph(neg_info, normal_text), "", "", "", ""])
        
        leaderboard_table = Table(leaderboard_data, colWidths=[0.8*inch, 2.4*inch, 0.8*inch, 0.8*inch, 1.1*inch, 1.1*inch])
        leaderboard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f0f0f0')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffacd')),
        ]))
        return [Paragraph("<b>Leaderboard</b>", leaderboard_title), Spacer(1, 0.1*inch), leaderboard_table]


    # 🎯 PART 4 OF 4: Textbook Style Questions Layout & Helper Encoder

    def _fetch_all_questions(self, quiz_id: int) -> List[Dict]:
        """Fetch all questions safely with options metrics"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, question_text, options, correct_answer, explanation FROM questions WHERE quiz_id = ? ORDER BY id ASC", (quiz_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            questions = []
            for idx, row in enumerate(rows, 1):
                q_id, q_text, options_json, correct_ans, explanation = row
                options = json.loads(options_json) if options_json else []
                try:
                    correct_idx = int(correct_ans)
                except:
                    try: correct_idx = options.index(str(correct_ans))
                    except: correct_idx = 0
                
                questions.append({
                    "number": idx, "text": q_text, "options": options,
                    "correct_idx": correct_idx, "explanation": explanation or "कोई व्याख्या नहीं है।"
                })
            return questions
        except Exception as e:
            self.logger.error(f"Error fetching questions: {e}")
            return []

    def _build_questions_section(self, questions_data: List[Dict], game_data: Dict, final_scores: Dict) -> List:
        """
        🔥 SCREENSHOT MATCHED LAYOUT: Generates clean question block 
        with colored Sahi Uttar, Hint, and subtle horizontal borders.
        """
        styles = getSampleStyleSheet()
        story = []
        
        # Styles definition matching image typography
        q_style = ParagraphStyle(
            'BookQuestion', parent=styles['Normal'], fontSize=11, leading=16,
            textColor=colors.HexColor('#000000'), fontName=self.default_font_bold, spaceAfter=4
        )
        ans_style = ParagraphStyle(
            'BookAnswer', parent=styles['Normal'], fontSize=10.5, leading=15,
            fontName=self.default_font, spaceAfter=3, leftIndent=15
        )
        hint_style = ParagraphStyle(
            'BookHint', parent=styles['Normal'], fontSize=10, leading=14,
            fontName=self.default_font, spaceAfter=8, leftIndent=15
        )
        
        for q_data in questions_data:
            q_text = self._sanitize_text(q_data["text"])  
            options = q_data["options"]
            c_idx = q_data["correct_idx"]
            
            # Correct answer text safely fetched
            correct_ans_text = self._sanitize_text(options[c_idx]) if c_idx < len(options) else "N/A"
            clean_exp = self._sanitize_text(q_data["explanation"])
            
            # 1. Question line
            story.append(Paragraph(f"<b>Q{q_data['number']}.</b> {q_text}", q_style))
            
            # 2. Sahi Uttar line (Green Label + Dark Red text)
            story.append(Paragraph(
                f"<font color='#16a34a'><b>Sahi Uttar:</b></font> <font color='#991b1b'><b>{correct_ans_text}</b></font>", 
                ans_style
            ))
            
            # 3. Hint line (Orange/Brown Label + Blue/Gray text description)
            story.append(Paragraph(
                f"<font color='#ea580c'><b>Hint:</b></font> <font color='#1e3a8a'>{clean_exp}</font>", 
                hint_style
            ))
            
            # 4. Divider Line between questions
            sep_table = Table([['']], colWidths=[7.7*inch])
            sep_table.setStyle(TableStyle([
                ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(sep_table)
            story.append(Spacer(1, 0.1*inch))
            
        return story
    
    def _sanitize_text(self, text: str) -> str:
        """Safely maps emojis into readable text icons without losing structural integrity"""
        if not text: return ""
        text = str(text)
        replacements = {
            '🏆': '[🏆]', '🌟': '[🌟]', '✨': '[✨]', '🔥': '[🔥]', '👑': '[👑]',
            '🎯': '[🎯]', '⚡': '[⚡]', '🎮': '[🎮]', '🤖': '[🤖]', '📚': '[📚]',
            '✅': '[Correct]', '❌': '[Wrong]', '🥇': '[1st]', '🥈': '[2nd]', '🥉': '[3rd]'
        }
        for emoji, rep in replacements.items():
            text = text.replace(emoji, rep)
        try:
            high_points = re.compile(r'[\U00010000-\U0010ffff]', re.UNICODE)
            text = high_points.sub(r'[⭐]', text)
        except: pass
        return text
    
    def _build_footer(self, quiz_title: str, total_players: int) -> List:
        styles = getSampleStyleSheet()
        footer_style = ParagraphStyle(
            'Footer', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#888888'), alignment=TA_CENTER, fontName=self.default_font
        )
        return [Paragraph(f"Report Summary: {total_players} participants", footer_style)]


def generate_quiz_pdf(
    chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0, db_file: str = "quiz_bot.db"
) -> Optional[BytesIO]:
    generator = QuizPDFGenerator(db_file=db_file)
    return generator.generate_quiz_report_pdf(chat_id, quiz_id, game_data, final_scores, negative_value)
  
