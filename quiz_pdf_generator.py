"""
🎯 Quiz PDF Report Generator
Generates comprehensive PDF reports for completed quizzes with:
- Quiz metadata (title, description, questions count)
- User leaderboard with scores
- All questions with options, correct answers, and explanations
- User responses tracking
- Visual styling with colors and formatting
"""

import json
import sqlite3
import logging
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Tuple, Optional

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY


class QuizPDFGenerator:
    """Generate comprehensive PDF reports for quiz results"""
    
    def __init__(self, db_file: str = "quiz_bot.db"):
        self.db_file = db_file
        self.logger = logging.getLogger(__name__)
        
    def generate_quiz_report_pdf(
        self, 
        chat_id: int,
        quiz_id: int,
        game_data: Dict,
        final_scores: Dict,
        negative_value: float = 0.0
    ) -> Optional[BytesIO]:
        """
        Generate a comprehensive PDF report of the quiz results
        
        Args:
            chat_id: Group chat ID where quiz was played
            quiz_id: Quiz ID from database
            game_data: Game state dictionary with poll info
            final_scores: Dictionary with user scores {user_id: {score, wrong, total_time, points}}
            negative_value: Negative marking applied
            
        Returns:
            BytesIO object containing PDF or None if error
        """
        try:
            pdf_buffer = BytesIO()
            
            # Fetch quiz and question data from DB
            quiz_title, quiz_desc, total_questions = self._fetch_quiz_data(quiz_id)
            questions_data = self._fetch_all_questions(quiz_id)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=A4,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch,
                title=f"Quiz Report - {quiz_title}"
            )
            
            # Build story (content) for PDF
            story = []
            
            # 1️⃣ HEADER SECTION
            story.extend(self._build_header(quiz_title, quiz_desc, total_questions))
            story.append(Spacer(1, 0.2*inch))
            
            # 2️⃣ LEADERBOARD SECTION
            story.extend(self._build_leaderboard(game_data, final_scores, negative_value))
            story.append(PageBreak())
            
            # 3️⃣ DETAILED QUESTIONS & ANSWERS SECTION
            story.extend(
                self._build_questions_section(
                    questions_data, 
                    game_data, 
                    final_scores
                )
            )
            
            # 4️⃣ FOOTER
            story.append(Spacer(1, 0.3*inch))
            story.extend(self._build_footer(quiz_title, len(final_scores)))
            
            # Build PDF
            doc.build(story)
            pdf_buffer.seek(0)
            
            self.logger.info(f"✅ PDF generated successfully for quiz {quiz_id}")
            return pdf_buffer
            
        except Exception as e:
            self.logger.error(f"❌ Error generating PDF: {e}", exc_info=True)
            return None
    
    def _fetch_quiz_data(self, quiz_id: int) -> Tuple[str, str, int]:
        """Fetch quiz metadata from database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT title, description FROM quizzes WHERE quiz_id = ?",
                (quiz_id,)
            )
            row = cursor.fetchone()
            
            cursor.execute(
                "SELECT COUNT(*) FROM questions WHERE quiz_id = ?",
                (quiz_id,)
            )
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
    
    def _fetch_all_questions(self, quiz_id: int) -> List[Dict]:
        """Fetch all questions with options, correct answers, and explanations"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT id, question_text, options, correct_answer, explanation, pre_message
                FROM questions 
                WHERE quiz_id = ?
                ORDER BY id ASC
                """,
                (quiz_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            questions = []
            for idx, row in enumerate(rows, 1):
                q_id, q_text, options_json, correct_ans, explanation, pre_msg = row
                options = json.loads(options_json) if options_json else []
                
                # 🟢 Convert correct_answer to INTEGER index
                try:
                    correct_idx = int(correct_ans)
                    if correct_idx < 0 or correct_idx >= len(options):
                        correct_idx = 0
                except (ValueError, TypeError):
                    try:
                        correct_idx = options.index(str(correct_ans))
                    except ValueError:
                        correct_idx = 0
                
                questions.append({
                    "number": idx,
                    "id": q_id,
                    "text": q_text,
                    "options": options,
                    "correct_idx": correct_idx,
                    "explanation": explanation or "No explanation provided",
                    "pre_message": pre_msg or ""
                })
            
            return questions
            
        except Exception as e:
            self.logger.error(f"Error fetching questions: {e}")
            return []
    
    def _build_header(self, quiz_title: str, quiz_desc: str, total_q: int) -> List:
        """Build PDF header with quiz title and metadata"""
        styles = getSampleStyleSheet()
        
        # Custom title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        desc_style = ParagraphStyle(
            'CustomDesc',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#555555'),
            spaceAfter=8,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )
        
        # Title
        title = Paragraph(f"📚 {quiz_title}", title_style)
        
        # Description
        description = Paragraph(f"<b>Description:</b> {quiz_desc}", desc_style)
        
        # Metadata
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = Paragraph(
            f"<b>Total Questions:</b> {total_q} | <b>Report Generated:</b> {now}",
            desc_style
        )
        
        # Divider line
        divider_data = [['']]
        divider_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f0f7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f4788')),
        ])
        divider = Table(divider_data, colWidths=[7.5*inch])
        divider.setStyle(divider_style)
        
        return [title, Spacer(1, 0.1*inch), description, metadata, Spacer(1, 0.1*inch), divider]
    
    def _build_leaderboard(
        self, 
        game_data: Dict, 
        final_scores: Dict, 
        negative_value: float
    ) -> List:
        """Build leaderboard section with rankings"""
        styles = getSampleStyleSheet()
        
        leaderboard_title = ParagraphStyle(
            'LeaderboardTitle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=10,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        # Sort scores
        sorted_scores = sorted(
            final_scores.items(),
            key=lambda x: (-x[1]["points"], x[1]["total_time"])
        )[:50]
        
        # Build leaderboard table
        leaderboard_data = [
            [
                Paragraph("<b>🏆 Rank</b>", styles['Normal']),
                Paragraph("<b>👤 Player</b>", styles['Normal']),
                Paragraph("<b>✅ Right</b>", styles['Normal']),
                Paragraph("<b>❌ Wrong</b>", styles['Normal']),
                Paragraph("<b>⏱ Time (sec)</b>", styles['Normal']),
                Paragraph("<b>🎯 Score</b>", styles['Normal'])
            ]
        ]
        
        for rank, (uid, meta) in enumerate(sorted_scores, 1):
            player_name = game_data.get("joined_users", {}).get(uid, f"User {uid}")
            
            rank_icon = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            
            leaderboard_data.append([
                Paragraph(rank_icon, styles['Normal']),
                Paragraph(player_name[:30], styles['Normal']),
                Paragraph(str(meta["score"]), styles['Normal']),
                Paragraph(str(meta["wrong"]), styles['Normal']),
                Paragraph(f"{meta['total_time']:.1f}", styles['Normal']),
                Paragraph(f"<b>{meta['points']:.2f}</b>", styles['Normal'])
            ])
        
        # Add negative marking info row
        leaderboard_data.append([
            Paragraph("", styles['Normal']),
            Paragraph(f"<i>Negative Marking: -{negative_value}/wrong</i>", styles['Normal']),
            "", "", "", ""
        ])
        
        # Create table with styling
        leaderboard_table = Table(
            leaderboard_data,
            colWidths=[0.8*inch, 2.2*inch, 0.8*inch, 0.8*inch, 1.0*inch, 1.0*inch]
        )
        
        leaderboard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f0f0f0')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffacd')),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Oblique'),
        ]))
        
        return [
            Paragraph("🏆 Leaderboard", leaderboard_title),
            Spacer(1, 0.1*inch),
            leaderboard_table
        ]
    
    def _build_questions_section(
        self, 
        questions_data: List[Dict],
        game_data: Dict,
        final_scores: Dict
    ) -> List:
        """Build detailed questions and answers section"""
        styles = getSampleStyleSheet()
        story = []
        
        section_title = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        question_title = ParagraphStyle(
            'QuestionTitle',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        normal_text = ParagraphStyle(
            'NormalText',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=4,
            alignment=TA_JUSTIFY
        )
        
        story.append(Paragraph("📝 Questions & Answers Review", section_title))
        story.append(Spacer(1, 0.15*inch))
        
        for q_data in questions_data:
            q_num = q_data["number"]
            q_text = q_data["text"]
            options = q_data["options"]
            correct_idx = q_data["correct_idx"]
            explanation = q_data["explanation"]
            
            # Question text
            question_para = Paragraph(
                f"<b>Q{q_num}. {q_text}</b>",
                question_title
            )
            story.append(question_para)
            
            # Options table
            options_data = []
            for opt_idx, opt_text in enumerate(options):
                is_correct = opt_idx == correct_idx
                mark = "✅" if is_correct else "⭕"
                color = colors.HexColor('#22c55e') if is_correct else colors.HexColor('#666666')
                
                options_data.append([
                    Paragraph(mark, normal_text),
                    Paragraph(f"<font color='{color.hexval()}'>{opt_text}</font>", normal_text)
                ])
            
            options_table = Table(options_data, colWidths=[0.4*inch, 6.5*inch])
            options_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            story.append(options_table)
            story.append(Spacer(1, 0.05*inch))
            
            # Explanation
            exp_para = Paragraph(
                f"<i><b>💡 Explanation:</b> {explanation}</i>",
                ParagraphStyle(
                    'Explanation',
                    parent=normal_text,
                    fontSize=9,
                    textColor=colors.HexColor('#555555'),
                    leftIndent=20
                )
            )
            story.append(exp_para)
            story.append(Spacer(1, 0.15*inch))
            
            # Page break every 3 questions to maintain readability
            if q_num % 3 == 0 and q_num < len(questions_data):
                story.append(PageBreak())
        
        return story
    
    def _build_footer(self, quiz_title: str, total_players: int) -> List:
        """Build PDF footer with summary info"""
        styles = getSampleStyleSheet()
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#888888'),
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        )
        
        footer_data = [
            Paragraph(
                f"📊 Report Summary: {total_players} participants | Quiz: {quiz_title}",
                footer_style
            ),
            Spacer(1, 0.05*inch),
            Paragraph(
                "Generated by 🤖 AI Quiz Bot | " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                footer_style
            )
        ]
        
        return footer_data


# Export function for easy integration
def generate_quiz_pdf(
    chat_id: int,
    quiz_id: int,
    game_data: Dict,
    final_scores: Dict,
    negative_value: float = 0.0,
    db_file: str = "quiz_bot.db"
) -> Optional[BytesIO]:
    """
    Convenience function to generate quiz PDF
    
    Returns BytesIO object ready to send as file
    """
    generator = QuizPDFGenerator(db_file)
    return generator.generate_quiz_report_pdf(chat_id, quiz_id, game_data, final_scores, negative_value)
