"""
🎯 Quiz PDF Report Generator - HINDI TEXT DISPLAY FIX
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
    """Generate comprehensive PDF reports for quiz results with Hindi text support"""
    
    def __init__(self, db_file: str = "quiz_bot.db"):
        self.db_file = db_file
        self.logger = logging.getLogger(__name__)
        self._register_fonts()

    def _register_fonts(self):
        """
        Download and register Devanagari fonts for Hindi support
        """
        try:
            font_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
            hindi_font_path = os.path.join(font_dir, "NotoSansDevanagari-Regular.ttf")
            hindi_bold_path = os.path.join(font_dir, "NotoSansDevanagari-Bold.ttf")
            
            # Download fonts if not present
            if not os.path.exists(hindi_font_path):
                self.logger.info("⏬ Downloading NotoSansDevanagari-Regular Font...")
                try:
                    urllib.request.urlretrieve(
                        "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansdevanagari/NotoSansDevanagari-Regular.ttf", 
                        hindi_font_path
                    )
                    self.logger.info("✅ Regular font downloaded successfully")
                except Exception as e:
                    self.logger.warning(f"Regular font download failed: {e}")
                    
            if not os.path.exists(hindi_bold_path):
                self.logger.info("⏬ Downloading NotoSansDevanagari-Bold Font...")
                try:
                    urllib.request.urlretrieve(
                        "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansdevanagari/NotoSansDevanagari-Bold.ttf", 
                        hindi_bold_path
                    )
                    self.logger.info("✅ Bold font downloaded successfully")
                except Exception as e:
                    self.logger.warning(f"Bold font download failed: {e}")

            # Register fonts
            font_registered = False
            if os.path.exists(hindi_font_path):
                try:
                    pdfmetrics.registerFont(TTFont('HindiFont', hindi_font_path))
                    self.default_font = 'HindiFont'
                    self.logger.info("✅ HindiFont registered")
                    font_registered = True
                except Exception as e:
                    self.logger.warning(f"Failed to register HindiFont: {e}")
            
            if not font_registered:
                self.default_font = 'Helvetica'
                self.logger.warning("⚠️ Using Helvetica fallback")
                
            bold_font_registered = False
            if os.path.exists(hindi_bold_path):
                try:
                    pdfmetrics.registerFont(TTFont('HindiFont-Bold', hindi_bold_path))
                    self.default_font_bold = 'HindiFont-Bold'
                    self.logger.info("✅ HindiFont-Bold registered")
                    bold_font_registered = True
                except Exception as e:
                    self.logger.warning(f"Failed to register HindiFont-Bold: {e}")
            
            if not bold_font_registered:
                self.default_font_bold = 'Helvetica-Bold'
                self.logger.warning("⚠️ Using Helvetica-Bold fallback")
                
        except Exception as e:
            self.logger.error(f"Font registration error: {e}")
            self.default_font = 'Helvetica'
            self.default_font_bold = 'Helvetica-Bold'
            
    def _fetch_quiz_data(self, quiz_id: int) -> Tuple[str, str, int]:
        """Fetch quiz metadata from database"""
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

    def generate_quiz_report_pdf(
        self, chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0
    ) -> Optional[BytesIO]:
        """Generate a comprehensive PDF report of the quiz results"""
        try:
            pdf_buffer = BytesIO()
            quiz_title, quiz_desc, total_questions = self._fetch_quiz_data(quiz_id)
            questions_data = self._fetch_all_questions(quiz_id)
            
            doc = SimpleDocTemplate(
                pdf_buffer, pagesize=A4, rightMargin=0.5*inch, leftMargin=0.5*inch, 
                topMargin=0.5*inch, bottomMargin=0.5*inch, title=f"Quiz Report"
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
        """Build PDF header"""
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'], fontSize=20,
            textColor=colors.HexColor('#1f4788'), spaceAfter=12, alignment=TA_CENTER, fontName=self.default_font_bold
        )
        desc_style = ParagraphStyle(
            'CustomDesc', parent=styles['Normal'], fontSize=11,
            textColor=colors.HexColor('#555555'), spaceAfter=8, alignment=TA_LEFT, fontName=self.default_font
        )
        
        # NO sanitization - let Hindi text pass as-is
        title = Paragraph(f"<b>{quiz_title}</b>", title_style)
        description = Paragraph(f"<b>Description:</b> {quiz_desc}", desc_style)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = Paragraph(f"<b>Total Questions:</b> {total_q} | <b>Generated:</b> {now}", desc_style)
        
        divider = Table([['']], colWidths=[7.5*inch])
        divider.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f0f7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f4788')),
        ]))
        return [title, Spacer(1, 0.1*inch), description, metadata, Spacer(1, 0.1*inch), divider]
    
    def _build_leaderboard(self, game_data: Dict, final_scores: Dict, negative_value: float) -> List:
        """Render leaderboard"""
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
            # NO sanitization for player names
            
            leaderboard_data.append([
                Paragraph(f"{rank}.", normal_text), 
                Paragraph(str(player_name)[:25], normal_text),
                Paragraph(str(meta["score"]), normal_text), 
                Paragraph(str(meta["wrong"]), normal_text),
                Paragraph(f"{meta['total_time']:.1f}", normal_text), 
                Paragraph(f"<b>{meta['points']:.2f}</b>", normal_text)
            ])
        
        neg_info = f"Negative Marking: -{negative_value}/wrong"
        leaderboard_data.append([Paragraph("", normal_text), Paragraph(neg_info, normal_text), "", "", "", ""])
        
        leaderboard_table = Table(leaderboard_data, colWidths=[0.8*inch, 2.2*inch, 0.8*inch, 0.8*inch, 1.0*inch, 1.0*inch])
        leaderboard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f0f0f0')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffacd')),
        ]))
        return [Paragraph("<b>Leaderboard</b>", leaderboard_title), Spacer(1, 0.1*inch), leaderboard_table]

    def _fetch_all_questions(self, quiz_id: int) -> List[Dict]:
        """Fetch all questions from database"""
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
                    correct_idx = 0
                
                questions.append({
                    "number": idx, "text": q_text, "options": options,
                    "correct_idx": correct_idx, "explanation": explanation or "No explanation"
                })
            return questions
        except Exception as e:
            self.logger.error(f"Error fetching questions: {e}")
            return []

    def _build_questions_section(self, questions_data: List[Dict], game_data: Dict, final_scores: Dict) -> List:
        """Render questions section"""
        styles = getSampleStyleSheet()
        story = []
        question_title = ParagraphStyle(
            'QuestionTitle', parent=styles['Heading3'], fontSize=11, textColor=colors.HexColor('#2c5aa0'), spaceAfter=6, fontName=self.default_font_bold
        )
        normal_text = ParagraphStyle(
            'NormalText', parent=styles['Normal'], fontSize=10, fontName=self.default_font
        )
        
        for q_data in questions_data:
            # NO sanitization - direct Hindi text
            q_text = q_data["text"]
            story.append(Paragraph(f"<b>Q{q_data['number']}. {q_text}</b>", question_title))
            
            options_data = []
            for opt_idx, opt_text in enumerate(q_data["options"]):
                is_correct = (opt_idx == q_data["correct_idx"])
                mark = "✓" if is_correct else "○"
                color = '#22c55e' if is_correct else '#666666'
                
                # NO sanitization - direct Hindi text for options
                options_data.append([
                    Paragraph(mark, normal_text), 
                    Paragraph(f"<font color='{color}'>{opt_text}</font>", normal_text)
                ])
            
            options_table = Table(options_data, colWidths=[0.5*inch, 6.5*inch])
            options_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(options_table)
            story.append(Spacer(1, 0.05*inch))
            
            # NO sanitization - direct Hindi text for explanation
            exp_text = q_data["explanation"]
            story.append(Paragraph(f"<b>Explanation:</b> {exp_text}", normal_text))
            story.append(Spacer(1, 0.15*inch))
        return story
    
    def _build_footer(self, quiz_title: str, total_players: int) -> List:
        """Footer section"""
        styles = getSampleStyleSheet()
        footer_style = ParagraphStyle(
            'Footer', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#888888'), alignment=TA_CENTER, fontName=self.default_font
        )
        return [Paragraph(f"Report Summary: {total_players} participants", footer_style)]

# Main function
def generate_quiz_pdf(
    chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0, db_file: str = "quiz_bot.db"
) -> Optional[BytesIO]:
    generator = QuizPDFGenerator(db_file=db_file)
    return generator.generate_quiz_report_pdf(chat_id, quiz_id, game_data, final_scores, negative_value)
