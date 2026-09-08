"""
🎯 Quiz Leaderboard PDF Generator - ONLY LEADERBOARD (PART 1 OF 4)
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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class QuizPDFGenerator:
    """Generate compact PDF reports containing ONLY the quiz leaderboard results"""
    
    def __init__(self, db_file: str = "quiz_bot.db"):
        self.db_file = db_file
        self.logger = logging.getLogger(__name__)
        self._register_fonts()


    # 🎯 PART 2 OF 4: Font setup aur database fetching logic (Class ke andar jodhein)

    def _register_fonts(self):
        """
        Termux और Android एनवायरनमेंट के लिए मजबूत हिंदी फॉन्ट रजिस्ट्रेशन
        """
        try:
            font_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
            hindi_font_path = os.path.join(font_dir, "NotoSansDevanagari-Regular.ttf")
            hindi_bold_path = os.path.join(font_dir, "NotoSansDevanagari-Bold.ttf")
            
            # GitHub से TrueType फाइल डाउनलोड करें
            if not os.path.exists(hindi_font_path):
                self.logger.info("⏬ Downloading NotoSansDevanagari for Termux...")
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
            
            # Global Styles Override
            styles = getSampleStyleSheet()
            styles['Normal'].fontName = 'HindiFont'
            styles['BodyText'].fontName = 'HindiFont'
            styles['Heading1'].fontName = 'HindiFont-Bold'
            styles['Heading2'].fontName = 'HindiFont-Bold'
                
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




    # 🎯 PART 3 OF 4: Document Flow Builder (Class ke andar jodhein)

    def generate_quiz_report_pdf(
        self, chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0, bot_username: str = "@QuizBot"
    ) -> Optional[BytesIO]:
        """Generate a PDF report containing ONLY the leaderboard with Bot Username"""
        try:
            pdf_buffer = BytesIO()
            quiz_title, quiz_desc, total_questions = self._fetch_quiz_data(quiz_id)
            
            # Margins सेट करें
            doc = SimpleDocTemplate(
                pdf_buffer, pagesize=A4, rightMargin=0.4*inch, leftMargin=0.4*inch, 
                topMargin=0.5*inch, bottomMargin=0.5*inch, title=f"Leaderboard - {quiz_title}"
            )
            
            story = []
            
            # 1️⃣ HEADER SECTION (Bot Username शामिल है)
            story.extend(self._build_header(quiz_title, quiz_desc, total_questions, bot_username))
            story.append(Spacer(1, 0.2*inch))
            
            # 2️⃣ LEADERBOARD SECTION
            story.extend(self._build_leaderboard(game_data, final_scores, negative_value))
            story.append(Spacer(1, 0.3*inch))
            
            # 3️⃣ FOOTER SECTION (Bot Username शामिल है)
            story.extend(self._build_footer(quiz_title, len(final_scores), bot_username))
            
            # PDF बिल्ड करें
            doc.build(story)
            pdf_buffer.seek(0)
            return pdf_buffer
        except Exception as e:
            self.logger.error(f"❌ Error generating Leaderboard PDF: {e}", exc_info=True)
            return None

    def _build_header(self, quiz_title: str, quiz_desc: str, total_q: int, bot_username: str) -> List:
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'], fontSize=20,
            textColor=colors.HexColor('#1f4788'), spaceAfter=4, alignment=TA_CENTER, fontName=self.default_font_bold
        )
        bot_style = ParagraphStyle(
            'BotUsernameHead', parent=styles['Normal'], fontSize=10,
            textColor=colors.HexColor('#2563eb'), spaceAfter=12, alignment=TA_CENTER, fontName=self.default_font_bold
        )
        desc_style = ParagraphStyle(
            'CustomDesc', parent=styles['Normal'], fontSize=11,
            textColor=colors.HexColor('#555555'), spaceAfter=8, alignment=TA_LEFT, fontName=self.default_font
        )
        
        title = Paragraph(f"<b>{self._sanitize_text(quiz_title)}</b>", title_style)
        bot_tag = Paragraph(f"Hosted by: {bot_username}", bot_style)
        description = Paragraph(f"<b>Description:</b> {self._sanitize_text(quiz_desc)}", desc_style)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = Paragraph(f"<b>Total Questions:</b> {total_q} | <b>Generated:</b> {now}", desc_style)
        
        divider = Table([['']], colWidths=[7.7*inch])
        divider.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f0f7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f4788')),
        ]))
        return [title, bot_tag, description, metadata, Spacer(1, 0.1*inch), divider]

    # 🎯 PART 4 OF 4: Leaderboard Matrix Table, Sanitizer aur Export function

    def _build_leaderboard(self, game_data: Dict, final_scores: Dict, negative_value: float) -> List:
        styles = getSampleStyleSheet()
        leaderboard_title = ParagraphStyle(
            'LeaderboardTitle', parent=styles['Heading2'], fontSize=15,
            textColor=colors.HexColor('#1f4788'), spaceAfter=10, fontName=self.default_font_bold
        )
        normal_text = ParagraphStyle('NormalText', parent=styles['Normal'], fontSize=10, fontName=self.default_font)
        bold_text = ParagraphStyle('BoldText', parent=styles['Normal'], fontSize=10, fontName=self.default_font_bold)
        
        # स्कोर सॉर्ट करें
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
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e1065')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f0f0f0')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffacd')),
        ]))
        return [Paragraph("<b>Leaderboard Results 🏆</b>", leaderboard_title), Spacer(1, 0.1*inch), leaderboard_table]
    
    def _sanitize_text(self, text: str) -> str:
        """क्रैश से बचने के लिए इमोजीस को टेक्स्ट ब्रैकेट आइकन्स में बदलता है"""
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
    
    def _build_footer(self, quiz_title: str, total_players: int, bot_username: str) -> List:
        styles = getSampleStyleSheet()
        footer_style = ParagraphStyle(
            'Footer', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#888888'), alignment=TA_CENTER, fontName=self.default_font
        )
        return [
            Paragraph(f"Report Summary: {total_players} participants played.", footer_style),
            Spacer(1, 0.04*inch),
            Paragraph(f"Generated by {bot_username} | " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), footer_style)
        ]


# ग्लोबल इंटीग्रेशन फ़ंक्शन (bot_username पैरामीटर के साथ)
def generate_quiz_pdf(
    chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0, bot_username: str = "@Di_Quiz_bot", db_file: str = "quiz_bot.db"
) -> Optional[BytesIO]:
    generator = QuizPDFGenerator(db_file=db_file)
    return generator.generate_quiz_report_pdf(chat_id, quiz_id, game_data, final_scores, negative_value, bot_username)
      
