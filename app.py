import os
from flask import Flask, request, jsonify, send_file
from openai import AzureOpenAI, OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from typing import List, Optional, Dict
from flask_cors import CORS  # Import CORS extension

class ResumeRefinementService:
    def __init__(self):
        """Initialize Azure OpenAI client with managed credentials."""
        try:
            # Azure OpenAI configuration
            self.client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "https://analytics-api-18-11.openai.azure.com/"),
                api_version="2024-02-15-preview",
                api_key=os.getenv("AZURE_OPENAI_API_KEY", "CGxtkPayWrod6afxgVgyv65mvxBnZrdhzTHB5NQu4C3f1dMkdvB1JQQJ99AKAC77bzfXJ3w3AAAAACOGyBzR")
            )

            # Azure-specific model deployment name
            self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
        except Exception as e:
            print(f"Azure OpenAI initialization error: {e}")
            self.client = None

    def refine_experience(self, details_text: str, max_bullets: int = 5) -> List[str]:
        """Refine job experience into professional, quantifiable bullet points."""
        if not self.client:
            return [details_text.split('.')[0] + '.']

        try:
            # Enhanced prompt for more professional and measurable bullet points
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""Convert job descriptions into {max_bullets} concise, impactful resume bullet points.
                        Key requirements:
                        - Use action verbs to start each bullet point
                        - Quantify achievements with metrics or percentages where possible
                        - Focus on results and impact, not just responsibilities
                        - Use consistent, professional language
                        - For every new point make it a bullet point and not a dasshed one
                        """
                    },
                    {
                        "role": "user",
                        "content": f"Transform these job responsibilities into professional, achievement-oriented bullet points:\n{details_text}"
                    }
                ],
                max_tokens=500,  # Increased token limit for more comprehensive refinement
                temperature=0.6,  # Slightly lower temperature for more consistent output
                top_p=0.8  # Added top_p for more focused responses
            )

            refined_text = response.choices[0].message.content
            refined_bullets = [
                bullet.strip()
                for bullet in refined_text.split('\n')
                if bullet.strip() and not bullet.startswith('•')
            ][:max_bullets]

            # Fallback if no bullets generated
            return refined_bullets if refined_bullets else [details_text.split('.')[0] + '.']

        except Exception as e:
            print(f"Experience refinement error: {e}")
            return [details_text.split('.')[0] + '.']

class ResumePDFGenerator:
    @staticmethod
    def create_resume_pdf(output_file: str, user_data: Dict, logo_path: Optional[str] = None,
                          refinement_service: Optional[ResumeRefinementService] = None):
        """Generate PDF resume with user information, logo, and improved spacing."""
        doc = SimpleDocTemplate(output_file, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Define custom styles
        title_style = ParagraphStyle(
            name='Title',
            fontName='Helvetica-Bold',
            fontSize=24,
            spaceAfter=12,
            alignment=1  # Centered
        )

        section_header_style = ParagraphStyle(
            name='SectionHeader',
            fontName='Helvetica-Bold',
            fontSize=16,
            spaceAfter=6,
            alignment=0,  # Left-aligned
            textColor=colors.darkblue
        )

        subheading_style = ParagraphStyle(
            name='Subheading',
            fontName='Helvetica-Bold',
            fontSize=12,
            spaceAfter=4,
            textColor=colors.black
        )

        normal_style = styles['Normal']
        normal_style.fontName = 'Helvetica'
        normal_style.fontSize = 11

        # Add logo if available
        if logo_path and os.path.exists(logo_path):
            elements.append(Image(logo_path, width=100, height=50))  # Logo size can be adjusted
            elements.append(Spacer(1, 12))  # Space below the logo

        # Header with name and contact info
        elements.append(Paragraph(f"<strong>{user_data['name']}</strong>", title_style))
        contact_info = f"{user_data.get('email', '')} | {user_data.get('phone', '')} | {user_data.get('linkedin', '')}"
        elements.append(Paragraph(contact_info, normal_style))
        elements.append(Spacer(1, 12))

        # Sections: Profile, Experience, Education, Skills
        sections = [
            ('Profile', user_data.get('profile', '')),
            ('Experience', [
                {
                    'header': f"<strong>{job['title']} | {job['company']} | {job['dates']}</strong>",
                    'details': refinement_service.refine_experience(job['details'])
                }
                for job in user_data.get('experience', [])
            ]),
            ('Education', [
                f"{edu['degree']} | {edu['institution']} | {edu['date']}"
                for edu in user_data.get('education', [])
            ]),
            ('Skills', user_data.get('skills', []))
        ]

        # Add sections with titles and content
        for title, content in sections:
            # Add section title with some spacing
            elements.append(Spacer(1, 12))  # Space before section title
            elements.append(Paragraph(f"<strong>{title}</strong>", section_header_style))

            if title == 'Experience':
                for job in content:
                    elements.append(Spacer(1, 6))  # Space before job title
                    elements.append(Paragraph(job['header'], subheading_style))
                    for detail in job['details']:
                        elements.append(Spacer(1, 6))  # Space between each bullet point
                        elements.append(Paragraph(f"{detail}", normal_style))
            elif isinstance(content, list):
                for item in content:
                    elements.append(Spacer(1, 6))  # Space between each item
                    elements.append(Paragraph(str(item), normal_style))
            else:
                elements.append(Spacer(1, 6))  # Space after single content
                elements.append(Paragraph(str(content), normal_style))

            # Add a divider line (this helps in separating sections more clearly)
            elements.append(Paragraph("<hr/>", normal_style))  # Horizontal line divider

        # Add page breaks after each major section (for a clean and structured look)
        elements.append(PageBreak())

        # Build the PDF
        doc.build(elements)

class ResumeGenerationApp:
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        self.refinement_service = ResumeRefinementService()
        self.logo_path = os.getenv("LOGO_PATH", "logo.png")  # Set default logo path
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/generate_resume', methods=['POST'])
        def generate_resume():
            try:
                user_data = request.json
                output_file = "generated_resume.pdf"
                ResumePDFGenerator.create_resume_pdf(output_file, user_data, self.logo_path, self.refinement_service)
                return send_file(output_file, as_attachment=True)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def run(self, debug: bool = True):
        self.app.run(debug=debug,host="localhost")

def main():
    resume_app = ResumeGenerationApp()
    resume_app.run()

if __name__ == "__main__":
    main()