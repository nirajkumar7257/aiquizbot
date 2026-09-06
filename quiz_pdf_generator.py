"""
🎯 Quiz PDF Report Generator - HINDI FONT SUPPORT FIX (PART 1 OF 4)
"""

import json
import sqlite3
import logging
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Tuple, Optional
import urllib.request  # 🚀 Auto-download Hindi font ke liye
import os

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class QuizPDFGenerator:
    """Generate comprehensive PDF reports for quiz results with Hindi/English support"""
    
    def __init__(self, db_file: str = "quiz_bot.db"):
        self.db_file = db_file
        self.logger = logging.getLogger(__name__)
        self._register_fonts()

    # 🎯 PART 2 OF 4: Font setup aur database logic (Class ke andar jodhein)

    def _register_fonts(self):
        """
        Register fonts that support Hindi/Devanagari characters flawlessly
        ✅ यह function Google Noto Sans Devanagari font को set up करता है
        """
        try:
            font_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
            hindi_font_path = os.path.join(font_dir, "NotoSansDevanagari-Regular.ttf")
            hindi_bold_path = os.path.join(font_dir, "NotoSansDevanagari-Bold.ttf")
            
            # Font files ko auto-download karein agar local me na milein
            if not os.path.exists(hindi_font_path):
                self.logger.info("⏬ Downloading NotoSansDevanagari Font for Hindi Support...")
                urllib.request.urlretrieve(
                    "https://github.com", 
                    hindi_font_path
                )
            if not os.path.exists(hindi_bold_path):
                urllib.request.urlretrieve(
                    "https://github.com", 
                    hindi_bold_path
                )

            # ReportLab me Font Register karein
            pdfmetrics.registerFont(TTFont('HindiFont', hindi_font_path))
            pdfmetrics.registerFont(TTFont('HindiFont-Bold', hindi_bold_path))
            
            self.default_font = 'HindiFont'
            self.default_font_bold = 'HindiFont-Bold'
            self.logger.info("✅ Hindi/Devanagari fonts registered successfully")
                
        except Exception as e:
            self.logger.warning(f"Font registration warning: {e}. Using fallback system fonts.")
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
            
            if not row:
                return "Unknown Quiz", "No description", 0
            
            title = row[0] or "Untitled Quiz"
            desc = row[1] or "No description provided"
            total_q = count_row[0] if count_row else 0
            return title, desc, total_q
        except Exception as e:
            self.logger.error(f"Error fetching quiz data: {e}")
            return "Unknown Quiz", "Error", 0


    # 🎯 PART 3 OF 4: Main builder, header aur leaderboard (Class ke andar jodhein)

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
                topMargin=0.5*inch, bottomMargin=0.5*inch, title=f"Quiz Report - {quiz_title}"
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
            self.logger.info(f"✅ PDF generated successfully for quiz {quiz_id}")
            return pdf_buffer
        except Exception as e:
            self.logger.error(f"❌ Error generating PDF: {e}", exc_info=True)
            return None

    def _build_header(self, quiz_title: str, quiz_desc: str, total_q: int) -> List:
        """Build PDF header with quiz title and metadata - WITH HINDI SUPPORT"""
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'], fontSize=22,
            textColor=colors.HexColor('#1f4788'), spaceAfter=12, alignment=TA_CENTER, fontName=self.default_font_bold
        )
        desc_style = ParagraphStyle(
            'CustomDesc', parent=styles['Normal'], fontSize=11,
            textColor=colors.HexColor('#555555'), spaceAfter=8, alignment=TA_LEFT, fontName=self.default_font
        )
        
        title = Paragraph(f"<b>{quiz_title}</b>", title_style)
        description = Paragraph(f"<b>Description:</b> {quiz_desc}", desc_style)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = Paragraph(f"<b>Total Questions:</b> {total_q} | <b>Report Generated:</b> {now}", desc_style)
        
        divider = Table([['']], colWidths=[7.5*inch])
        divider.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f0f7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f4788')),
        ]))
        return [title, Spacer(1, 0.1*inch), description, metadata, Spacer(1, 0.1*inch), divider]
    
    def _build_leaderboard(self, game_data: Dict, final_scores: Dict, negative_value: float) -> List:
        """Build leaderboard section with rankings - WITH HINDI SUPPORT"""
        styles = getSampleStyleSheet()
        leaderboard_title = ParagraphStyle(
            'LeaderboardTitle', parent=styles['Heading2'], fontSize=16,
            textColor=colors.HexColor('#1f4788'), spaceAfter=10, alignment=TA_LEFT, fontName=self.default_font_bold
        )
        normal_text = ParagraphStyle('NormalText', parent=styles['Normal'], fontSize=10, fontName=self.default_font)
        
        sorted_scores = sorted(final_scores.items(), key=lambda x: (-x[1]["points"], x[1]["total_time"]))[:50]
        leaderboard_data = [[
            Paragraph("<b>Rank</b>", normal_text), Paragraph("<b>Player Name</b>", normal_text),
            Paragraph("<b>Right</b>", normal_text), Paragraph("<b>Wrong</b>", normal_text),
            Paragraph("<b>Time (sec)</b>", normal_text), Paragraph("<b>Score</b>", normal_text)
        ]]
        
        for rank, (uid, meta) in enumerate(sorted_scores, 1):
            player_name = game_data.get("joined_users", {}).get(uid, f"User {uid}")
            player_name = self._sanitize_text(player_name)
            leaderboard_data.append([
                Paragraph(f"{rank}.", normal_text), Paragraph(player_name[:30], normal_text),
                Paragraph(str(meta["score"]), normal_text), Paragraph(str(meta["wrong"]), normal_text),
                Paragraph(f"{meta['total_time']:.1f}", normal_text), Paragraph(f"<b>{meta['points']:.2f}</b>", normal_text)
            ])
        
        neg_info = f"Negative Marking: -{negative_value}/wrong"
        leaderboard_data.append([Paragraph("", normal_text), Paragraph(neg_info, normal_text), "", "", "", ""])
        
        leaderboard_table = Table(leaderboard_data, colWidths=[0.8*inch, 2.2*inch, 0.8*inch, 0.8*inch, 1.0*inch, 1.0*inch])
        leaderboard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.default_font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 11), ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige), ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f0f0f0')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffacd')),
            ('FONTSIZE', (0, -1), (-1, -1), 9), ('FONTNAME', (0, -1), (-1, -1), self.default_font),
        ]))
        return [Paragraph("<b>Leaderboard</b>", leaderboard_title), Spacer(1, 0.1*inch), leaderboard_table]


    # 🎯 PART 4 OF 4: Questions, helper methods aur wrapper integration

    def _fetch_all_questions(self, quiz_id: int) -> List[Dict]:
        """Fetch all questions with options, correct answers, and explanations"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, question_text, options, correct_answer, explanation, pre_message "
                "FROM questions WHERE quiz_id = ? ORDER BY id ASC", (quiz_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            questions = []
            for idx, row in enumerate(rows, 1):
                q_id, q_text, options_json, correct_ans, explanation, pre_msg = row
                options = json.loads(options_json) if options_json else []
                
                try:
                    correct_idx = int(correct_ans)
                    if correct_idx < 0 or correct_idx >= len(options): correct_idx = 0
                except (ValueError, TypeError):
                    try: correct_idx = options.index(str(correct_ans))
                    except ValueError: correct_idx = 0
                
                questions.append({
                    "number": idx, "id": q_id, "text": q_text, "options": options,
                    "correct_idx": correct_idx, "explanation": explanation or "No explanation provided",
                    "pre_message": pre_msg or ""
                })
            return questions
        except Exception as e:
            self.logger.error(f"Error fetching questions: {e}")
            return []

    def _build_questions_section(self, questions_data: List[Dict], game_data: Dict, final_scores: Dict) -> List:
        """Build detailed questions and answers section - WITH HINDI SUPPORT"""
        styles = getSampleStyleSheet()
        story = []
        section_title = ParagraphStyle(
            'SectionTitle', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#1f4788'), spaceAfter=12, alignment=TA_LEFT, fontName=self.default_font_bold
        )
        question_title = ParagraphStyle(
            'QuestionTitle', parent=styles['Heading3'], fontSize=12, textColor=colors.HexColor('#2c5aa0'), spaceAfter=6, fontName=self.default_font_bold
        )
        normal_text = ParagraphStyle(
            'NormalText', parent=styles['Normal'], fontSize=10, spaceAfter=4, alignment=TA_JUSTIFY, fontName=self.default_font
        )
        
        story.append(Paragraph("<b>Questions & Answers Review</b>", section_title))
        story.append(Spacer(1, 0.15*inch))
        
        for q_data in questions_data:
            q_num = q_data["number"]
            q_text = self._sanitize_text(q_data["text"])  
            options = [self._sanitize_text(opt) for opt in q_data["options"]]  
            correct_idx = q_data["correct_idx"]
            explanation = self._sanitize_text(q_data["explanation"])  
            
            story.append(Paragraph(f"<b>Q{q_num}. {q_text}</b>", question_title))
            
            options_data = []
            for opt_idx, opt_text in enumerate(options):
                is_correct = opt_idx == correct_idx
                mark = "CORRECT" if is_correct else "OPTION"
                color = '#22c55e' if is_correct else '#666666'
                options_data.append([Paragraph(mark, normal_text), Paragraph(f"<font color='{color}'>{opt_text}</font>", normal_text)])
            
            options_table = Table(options_data, colWidths=[1.0*inch, 6.0*inch])
            options_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (-1, -1), self.default_font), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(options_table)
            story.append(Spacer(1, 0.05*inch))
            
            exp_para = Paragraph(f"<b>Explanation:</b> {explanation}", ParagraphStyle(
                'Explanation', parent=normal_text, fontSize=9, textColor=colors.HexColor('#555555'), leftIndent=20, fontName=self.default_font
            ))
            story.append(exp_para)
            story.append(Spacer(1, 0.15*inch))
            
            if q_num % 3 == 0 and q_num < len(questions_data):
                story.append(PageBreak())
        return story
    
    def _sanitize_text(self, text: str) -> str:
        """Remove problematic emojis that cause layout breaks, keeping Hindi fully intact."""
        if not text: return ""
        text = str(text)
        replacements = {
            '📚': '', '✅': '[Correct]', '❌': '[Wrong]', '💡': '', '🏆': '', 
            '⏱': '', '🎯': '', '🥇': '1st', '🥈': '2nd', '🥉': '3rd', 
            '➻': '->', '🔹': '*', '━': '-', '│': '|', '┈': '-'
        }
        for emoji, replacement in replacements.items():
            text = text.replace(emoji, replacement)
        return text
    
    def _build_footer(self, quiz_title: str, total_players: int) -> List:
        """Build PDF footer with summary info"""
        styles = getSampleStyleSheet()
        footer_style = ParagraphStyle(
            'Footer', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#888888'), alignment=TA_CENTER, fontName=self.default_font
        )
        return [
            Paragraph(f"Report Summary: {total_players} participants | Quiz: {quiz_title}", footer_style),
            Spacer(1, 0.05*inch),
            Paragraph("Generated by AI Quiz Bot | " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), footer_style)
        ]

# Export function for easy integration
def generate_quiz_pdf(
    chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0, db_file: str = "quiz_bot.db"
) -> Optional[BytesIO]:
    generator = QuizPDFGenerator(db_file=db_file)
    return generator.generate_quiz_report_pdf(chat_id, quiz_id, game_data, final_scores, negative_value)
        
