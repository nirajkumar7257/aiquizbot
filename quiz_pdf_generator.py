"""
🎯 Quiz PDF Report Generator - COMPLETE HINDI & EMOJI FIX (PART 1 OF 4)
Uses fpdf2 with text shaping for flawless Hindi layout and emoji rendering.
"""

import json
import sqlite3
import logging
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Tuple, Optional
import urllib.request
import os

# 🔥 ReportLab ki jagah fpdf2 ka use
from fpdf import FPDF

class QuizPDFGenerator:
    """Generate comprehensive PDF reports for quiz results with native Hindi & Emoji support"""
    
    def __init__(self, db_file: str = "quiz_bot.db"):
        self.db_file = db_file
        self.logger = logging.getLogger(__name__)

    # 🎯 PART 2 OF 4: Font Setup aur DB Logic (Class ke andar jodhein)

    def _setup_pdf_fonts(self, pdf: FPDF):
        """
        Google Noto Fonts download aur register karne ka logic
        jo Hindi layout aur complex emojis ko smoothly handle karta hai.
        """
        try:
            font_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
            
            # Fonts ke paths define karein
            hindi_reg = os.path.join(font_dir, "NotoSansDevanagari-Regular.ttf")
            hindi_bold = os.path.join(font_dir, "NotoSansDevanagari-Bold.ttf")
            emoji_font = os.path.join(font_dir, "NotoColorEmoji.ttf")
            
            # ⏬ Auto-download fonts agar local me nahi milte
            if not os.path.exists(hindi_reg):
                urllib.request.urlretrieve(
                    "https://github.com", hindi_reg
                )
            if not os.path.exists(hindi_bold):
                urllib.request.urlretrieve(
                    "https://github.com", hindi_bold
                )
            if not os.path.exists(emoji_font):
                urllib.request.urlretrieve(
                    "https://github.com", emoji_font
                )

            # 🔥 FPDF2 me Text Shaping aur Fonts Add karein
            pdf.add_font("Hindi", "", hindi_reg, uni=True)
            pdf.add_font("Hindi-Bold", "", hindi_bold, uni=True)
            pdf.add_font("Emoji", "", emoji_font, uni=True)
            
            # Global Font fallback aur text shaping enable karein
            pdf.set_font_fallback("Emoji")
            pdf.set_text_shaping(True)
            
        except Exception as e:
            self.logger.warning(f"Font setup failed, falling back to core fonts: {e}")
            pdf.add_font("Hindi", "", "Helvetica")

    def _fetch_quiz_data(self, quiz_id: int) -> Tuple[str, str, int]:
        """Database se quiz details fetch karne ke liye"""
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


    # 🎯 PART 3 OF 4: Main Builder aur Leaderboard Flow (Class ke andar jodhein)

    def generate_quiz_report_pdf(
        self, chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0
    ) -> Optional[BytesIO]:
        """Generate a comprehensive PDF report using FPDF2"""
        try:
            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.set_margin(12)
            self._setup_pdf_fonts(pdf)
            pdf.add_page()
            
            quiz_title, quiz_desc, total_questions = self._fetch_quiz_data(quiz_id)
            questions_data = self._fetch_all_questions(quiz_id)
            
            # 1️⃣ HEADER SECTION
            pdf.set_font("Hindi-Bold", size=20)
            pdf.set_text_color(31, 71, 136) # Hex #1f4788
            pdf.cell(0, 12, text=quiz_title, ln=True, align="C")
            
            pdf.set_font("Hindi", size=10)
            pdf.set_text_color(85, 85, 85)
            pdf.multi_cell(0, 6, text=f"Description: {quiz_desc}")
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pdf.cell(0, 6, text=f"Total Questions: {total_questions} | Report Generated: {now}", ln=True)
            
            # Divider Line
            pdf.set_draw_color(31, 71, 136)
            pdf.line(12, pdf.get_y() + 2, 198, pdf.get_y() + 2)
            pdf.ln(6)
            
            # 2️⃣ LEADERBOARD SECTION
            pdf.set_font("Hindi-Bold", size=14)
            pdf.set_text_color(31, 71, 136)
            pdf.cell(0, 10, text="Leaderboard 🏆", ln=True)
            
            # Table Headers
            pdf.set_font("Hindi-Bold", size=10)
            pdf.set_text_color(255, 255, 255)
            pdf.set_fill_color(31, 71, 136)
            
            cols = [15, 65, 20, 20, 30, 25] # total 175mm width
            headers = ["Rank", "Player Name", "Right", "Wrong", "Time (s)", "Score"]
            for col_w, header in zip(cols, headers):
                pdf.cell(col_w, 8, text=header, border=1, align="C", fill=True)
            pdf.ln()
            
            # Table Data Rows
            pdf.set_font("Hindi", size=10)
            pdf.set_text_color(0, 0, 0)
            
            sorted_scores = sorted(final_scores.items(), key=lambda x: (-x[1]["points"], x[1]["total_time"]))[:50]
            
            for rank, (uid, meta) in enumerate(sorted_scores, 1):
                # User ka name kaisa bhi ho (Hindi/Emoji), raw extract karein
                player_name = game_data.get("joined_users", {}).get(str(uid), game_data.get("joined_users", {}).get(int(uid), f"User {uid}"))
                player_name = str(player_name)[:30]
                
                # Zebra row coloring
                fill = (rank % 2 == 0)
                pdf.set_fill_color(240, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
                
                pdf.cell(cols[0], 7, text=f"{rank}.", border=1, align="C", fill=True)
                pdf.cell(cols[1], 7, text=player_name, border=1, fill=True) # Full emoji & hindi supported cell
                pdf.cell(cols[2], 7, text=str(meta["score"]), border=1, align="C", fill=True)
                pdf.cell(cols[3], 7, text=str(meta["wrong"]), border=1, align="C", fill=True)
                pdf.cell(cols[4], 7, text=f"{meta['total_time']:.1f}", border=1, align="C", fill=True)
                pdf.cell(cols[5], 7, text=f"{meta['points']:.2f}", border=1, align="C", fill=True)
                pdf.ln()
                
            # 3️⃣ QUESTIONS SECTION FLOW CALL
            pdf.add_page()
            self._build_fpdf_questions(pdf, questions_data)
            
            # Output to Buffer
            pdf_buffer = BytesIO()
            pdf.output(pdf_buffer)
            pdf_buffer.seek(0)
            return pdf_buffer
            
        except Exception as e:
            self.logger.error(f"❌ Error generating PDF: {e}", exc_info=True)
            return None

    # 🎯 PART 4 OF 4: Questions Block aur Main Wrapper (Class ke andar jodhein)

    def _fetch_all_questions(self, quiz_id: int) -> List[Dict]:
        """Database se questions fetch karne ke liye"""
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
                    "correct_idx": correct_idx, "explanation": explanation or "No explanation provided"
                })
            return questions
        except Exception as e:
            self.logger.error(f"Error fetching questions: {e}")
            return []

    def _build_fpdf_questions(self, pdf: FPDF, questions_data: List[Dict]):
        """Sawaal-Jawaab section jisme Hindi aur Emojis native render hote hain"""
        pdf.set_font("Hindi-Bold", size=14)
        pdf.set_text_color(31, 71, 136)
        pdf.cell(0, 10, text="Questions & Answers Review 📝", ln=True)
        pdf.ln(2)
        
        for q_data in questions_data:
            # Sawaal print karein
            pdf.set_font("Hindi-Bold", size=11)
            pdf.set_text_color(44, 90, 160)
            pdf.multi_cell(0, 6, text=f"Q{q_data['number']}. {q_data['text']}")
            pdf.ln(1)
            
            # Options list render karein
            pdf.set_font("Hindi", size=10)
            pdf.set_text_color(0, 0, 0)
            for opt_idx, opt_text in enumerate(q_data["options"]):
                is_correct = (opt_idx == q_data["correct_idx"])
                prefix = "✅ [CORRECT] " if is_correct else "🔹 [OPTION] "
                
                if is_correct:
                    pdf.set_text_color(34, 197, 94) # Green color
                else:
                    pdf.set_text_color(102, 102, 102) # Grey color
                    
                pdf.multi_cell(0, 5, text=f"   {prefix}{opt_text}")
                
            # Explanation block
            pdf.ln(1)
            pdf.set_font("Hindi", size=9)
            pdf.set_text_color(85, 85, 85)
            pdf.multi_cell(0, 5, text=f"💡 Explanation: {q_data['explanation']}")
            pdf.ln(4)

# Global helper function project integration ke liye
def generate_quiz_pdf(
    chat_id: int, quiz_id: int, game_data: Dict, final_scores: Dict, negative_value: float = 0.0, db_file: str = "quiz_bot.db"
) -> Optional[BytesIO]:
    generator = QuizPDFGenerator(db_file=db_file)
    return generator.generate_quiz_report_pdf(chat_id, quiz_id, game_data, final_scores, negative_value)
    
