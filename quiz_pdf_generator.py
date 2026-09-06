"""
🎯 Quiz PDF Report Generator - HINDI TEXT DISPLAY FIX (NO SANITIZATION)
"""

import json
import sqlite3
import logging
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
        self.default_font = 'Helvetica'
        self.default_font_bold = 'Helvetica-Bold'
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
            if os.path.exists(hindi_font_path):
                try:
                    pdfmetrics.registerFont(TTFont('HindiFont', hindi_font_path))
                    self.default_font = 'HindiFont'
                    self.logger.info("✅ HindiFont registered successfully")
                except Exception as e:
                    self.logger.warning(f"Failed to register HindiFont: {e}")
                    self.default_font = 'Helvetica'
            
            if os.path.exists(hindi_bold_path):
                try:
                    pdfmetrics.registerFont(TTFont('HindiFont-Bold', hindi_bold_path))
                    self.default_font_bold = 'HindiFont-Bold'
                    self.logger.info("✅ HindiFont-Bold registered successfully")
                except Exception as e:
                    self.logger.warning(f"Failed to register HindiFont-Bold: {e}")
                    self.default_font_bold = 'Helvetica-Bold'
                
        except Exception as e:
            self.logger.error(f"Font registration error: {e}")
            self.default_font = 'Helvetica'
            self.default_font_bold = 'Helvetica-Bold'
            
    def _create_styles(self) -> Dict:
        """
        Create all paragraph styles with HINDI FONTS
        ✅ यह ensure करता है कि हर style को Hindi font मिले
        """
        styles = {}
        
        # Title Style
        styles['Title'] = ParagraphStyle(
            'CustomTitle',
            fontSize=20,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName=self.default_font_bold,
            leading=24
        )
        
        # Description/Normal Style
        styles['Normal'] = ParagraphStyle(
            'CustomNormal',
            fontSize=11,
            textColor=colors.HexColor('#555555'),
            spaceAfter=8,
            alignment=TA_LEFT,
            fontName=self.default_font,
            leading=14
        )
        
        # Leaderboard Title
        styles['LeaderboardTitle'] = ParagraphStyle(
            'LeaderboardTitle',
            fontSize=15,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=10,
            fontName=self.default_font_bold,
            leading=18
        )
        
        # Question Title
        styles['QuestionTitle'] = ParagraphStyle(
            'QuestionTitle',
            fontSize=11,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=6,
            fontName=self.default_font_bold,
            leading=14
        )
        
        # Normal Text for tables
        styles['NormalText'] = ParagraphStyle(
            'NormalText',
            fontSize=10,
            fontName=self.default_font,
            leading=12
        )
        
        # Bold Text for tables
        styles['BoldText'] = ParagraphStyle(
            'BoldText',
            fontSize=10,
            fontName=self.default_font_bold,
            leading=12
        )
        
        # Footer
        styles['Footer'] = ParagraphStyle(
            'Footer',
            fontSize=9,
            textColor=colors.HexColor('#888888'),
            alignment=TA_CENTER,
            fontName=self.default_font,
            leading=11
        )
        
        return styles
            
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
        styles = self._create_styles()
        
        title = Paragraph(f"<b>{quiz_title}</b>", styles['Title'])
        description = Paragraph(f"<b>Description:</b> {quiz_desc}", styles['Normal'])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = Paragraph(f"<b>Total Questions:</b> {total_q} | <b>Generated:</b> {now}", styles['Normal'])
        
        divider = Table([['']], colWidths=[7.5*inch])
        divider.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f0f7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f4788')),
        ]))
        return [title, Spacer(1, 0.1*inch), description, metadata, Spacer(1, 0.1*inch), divider]
    
    def _build_leaderboard(self, game_data: Dict, final_scores: Dict, negative_value: float) -> List:
        """Render leaderboard"""
        styles = self._create_styles()
        
        sorted_scores = sorted(final_scores.items(), key=lambda x: (-x[1]["points"], x[1]["total_time"]))[:50]
        leaderboard_data = [[
            Paragraph("<b>Rank</b>", styles['BoldText']), 
            Paragraph("<b>Player Name</b>", styles['BoldText']),
            Paragraph("<b>Right</b>", styles['BoldText']), 
            Paragraph("<b>Wrong</b>", styles['BoldText']),
            Paragraph("<b>Time (s)</b>", styles['BoldText']), 
            Paragraph("<b>Score</b>", styles['BoldText'])
        ]]
        
        for rank, (uid, meta) in enumerate(sorted_scores, 1):
            player_name = game_data.get("joined_users", {}).get(str(uid), game_data.get("joined_users", {}).get(int(uid), f"User {uid}"))
            
            leaderboard_data.append([
                Paragraph(f"{rank}.", styles['NormalText']), 
                Paragraph(str(player_name)[:25], styles['NormalText']),
                Paragraph(str(meta["score"]), styles['NormalText']), 
                Paragraph(str(meta["wrong"]), styles['NormalText']),
                Paragraph(f"{meta['total_time']:.1f}", styles['NormalText']), 
                Paragraph(f"<b>{meta['points']:.2f}</b>", styles['NormalText'])
            ])
        
        neg_info = f"Negative Marking: -{negative_value}/wrong"
        leaderboard_data.append([Paragraph("", styles['NormalText']), Paragraph(neg_info, styles['NormalText']), "", "", "", ""])
        
        leaderboard_table = Table(leaderboard_data, colWidths=[0.8*inch, 2.2*inch, 0.8*inch, 0.8*inch, 1.0*inch, 1.0*inch])
        leaderboard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f0f0f0')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffacd')),
        ]))
        return [Paragraph("<b>Leaderboard</b>", styles['LeaderboardTitle']), Spacer(1, 0.1*inch), leaderboard_table]

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
        styles = self._create_styles()
        story = []
        
        for q_data in questions_data:
            q_text = q_data["text"]
            story.append(Paragraph(f"<b>Q{q_data['number']}. {q_text}</b>", styles['QuestionTitle']))
            
            options_data = []
            for opt_idx, opt_text in enumerate(q_data["options"]):
                is_correct = (opt_idx == q_data["correct_idx"])
                mark = "✓" if is_correct else "○"
                color = '#22c55e' if is_correct else '#666666'
                
                options_data.append([
                    Paragraph(mark, styles['NormalText']), 
                    Paragraph(f"<font color='{color}'>{opt_text}</font>", styles['NormalText'])
                ])
            
            options_table = Table(options_data, colWidths=[0.5*inch, 6.5*inch])
            options_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'), 
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(options_table)
            story.append(Spacer(1, 0.05*inch))
            
            exp_text = q_data["explanation"]
            story.append(Paragraph(f"<b>Explanation:</b> {exp_text}", styles['NormalText']))
            story.append(Spacer(1, 0.15*inch))
        return story
    
    def _build_footer(self, quiz_title: str, total_players: int) -> List:
        """Footer section"""
        styles = self._create_styles()
        return [Paragraph(f"Report Summary: {total_players} participants", styles['Footer'])]

# Main function
def generate_quiz_pdf(
    chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0, db_file: str = "quiz_bot.db"
) -> Optional[BytesIO]:
    generator = QuizPDFGenerator(db_file=db_file)
    return generator.generate_quiz_report_pdf(chat_id, quiz_id, game_data, final_scores, negative_value)
