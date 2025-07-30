from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import os
import logging
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from dotenv import load_dotenv
from groq import Groq
import re
import tempfile
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
PORT = int(os.getenv('PORT', 5000))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Document types
DOCUMENT_TYPES = {
    'affidavit': 'Affidavit Document',
    'letter': 'Formal Letter', 
    'contract': 'Contract/Agreement',
    'certificate': 'Certificate',
    'application': 'Application Form',
    'custom': 'Custom Document'
}

class DocumentGenerator:
    @staticmethod
    def generate_pdf(text: str, title: str, user_data: dict) -> str:
        try:
            # Create temporary file with proper naming
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix='doc_')
            filepath = temp_file.name
            temp_file.close()
            
            doc = SimpleDocTemplate(filepath, pagesize=A4, 
                                  rightMargin=72, leftMargin=72, 
                                  topMargin=72, bottomMargin=72)
            
            styles = getSampleStyleSheet()
            
            # Enhanced styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                textColor=colors.black
            )
            
            content_style = ParagraphStyle(
                'ContentStyle',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=15,
                leading=18,
                fontName='Helvetica',
                textColor=colors.black,
                alignment=TA_LEFT
            )
            
            heading_style = ParagraphStyle(
                'HeadingStyle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                spaceBefore=20,
                fontName='Helvetica-Bold',
                textColor=colors.black
            )
            
            signature_style = ParagraphStyle(
                'SignatureStyle',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=6,
                fontName='Helvetica',
                alignment=TA_RIGHT
            )
            
            elements = []
            
            # Add title
            elements.append(Paragraph(title.upper(), title_style))
            elements.append(Spacer(1, 30))
            
            # Add date
            current_date = datetime.now().strftime("%B %d, %Y")
            elements.append(Paragraph(f"<b>Date:</b> {current_date}", content_style))
            elements.append(Spacer(1, 25))
            
            # Process and add main content with better formatting
            clean_text = str(text).replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            
            # Split content into paragraphs and format
            paragraphs = clean_text.split('\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    # Check if it's a heading (starts with number or capital letters)
                    if para.isupper() or para.startswith(('1.', '2.', '3.', '4.', '5.', 'ARTICLE', 'SECTION')):
                        elements.append(Paragraph(para, heading_style))
                    else:
                        elements.append(Paragraph(para, content_style))
                    elements.append(Spacer(1, 10))
            
            # Add signature section
            elements.append(Spacer(1, 40))
            elements.append(Paragraph("_" * 40, signature_style))
            elements.append(Paragraph("Signature & Date", signature_style))
            
            doc.build(elements)
            logger.info(f"PDF generated successfully: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            raise Exception(f"PDF generation failed: {str(e)}")

def extract_user_data(text: str) -> dict:
    """Extract user data from text"""
    data = {}
    
    # Name patterns
    name_patterns = [
        r"(?:my name is|i am|name:?)\\s*([A-Za-z\\s]+)",
        r"([A-Z][a-z]+\\s+[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)"
    ]
    
    # Address patterns
    address_patterns = [
        r"(?:address|live at|residing at|from):?\\s*([^.\\n]+(?:\\d{6}|\\d{3}\\s*\\d{3})[^.\\n]*)"
    ]
    
    # Extract name
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and len(match.group(1).strip().split()) >= 2:
            data['full_name'] = match.group(1).strip()
            break
    
    # Extract address
    for pattern in address_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['address'] = match.group(1).strip()
            break
    
    return data

def generate_ai_response(prompt: str, document_type: str) -> str:
    """Generate AI response using Groq API"""
    if not groq_client:
        if not GROQ_API_KEY:
            return "❌ GROQ_API_KEY not found. Please add it in Railway Variables."
        return "❌ AI service not available. Please check configuration."
    
    try:
        system_prompts = {
            'affidavit': "You are an expert legal document writer. Create a complete, professional affidavit with proper legal format, including: 1) Clear title 2) Declarant information 3) Statement of facts 4) Oath clause 5) Signature section. Use formal legal language and proper structure.",
            'letter': "You are a professional business letter writer. Create a complete formal letter with: 1) Sender details 2) Date 3) Recipient details 4) Subject line 5) Professional salutation 6) Clear body paragraphs 7) Appropriate closing. Use professional tone and proper business format.",
            'contract': "You are a contract specialist. Create a comprehensive contract with: 1) Clear title 2) Parties involved 3) Terms and conditions 4) Payment details 5) Duration 6) Termination clauses 7) Signature sections. Use precise legal language.",
            'certificate': "You are creating official certificates. Generate a formal certificate with: 1) Official header 2) Certificate title 3) Recipient name 4) Achievement/completion details 5) Date 6) Authority signature section. Use formal, official language.",
            'application': "You are an expert in applications. Create authentic applications with: 1) Application title 2) Applicant details 3) Purpose/reason 4) Supporting information 5) Declaration 6) Signature section. Use formal, respectful language.",
            'general': "You are a professional document assistant. Create well-structured, professional documents with proper formatting, clear sections, and appropriate language for the requested document type."
        }
        
        system_prompt = system_prompts.get(document_type, system_prompts['general'])
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a professional {document_type} document based on this request: {prompt}\n\nFormatting Requirements:\n- Use clear section headings in UPPERCASE\n- Structure content in numbered points where appropriate\n- Include all necessary legal/formal elements\n- Use professional, formal language\n- Make it complete and ready to use\n- Include placeholder fields like [NAME], [ADDRESS], [DATE] where needed\n- Ensure proper paragraph spacing\n- Add appropriate legal disclaimers if required\n\nPlease create a well-structured, professional document that follows standard formatting conventions."}
            ],
            model="llama3-70b-8192",
            temperature=0.2,
            max_tokens=3000
        )
        
        return chat_completion.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        error_msg = str(e)
        if "json" in error_msg.lower():
            return "❌ API response format error. Please try again."
        elif "rate limit" in error_msg.lower():
            return "❌ Rate limit exceeded. Please wait and try again."
        elif "invalid" in error_msg.lower():
            return "❌ Invalid API key. Please check your GROQ_API_KEY."
        return f"❌ AI service error: {error_msg[:100]}..."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        message = data.get('message', '').strip()
        document_type = data.get('document_type', 'general')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Generate AI response
        ai_response = generate_ai_response(message, document_type)
        
        return jsonify({
            'response': ai_response,
            'document_type': document_type,
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({
            'error': f'Server error: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/generate-document', methods=['POST'])
def generate_document():
    try:
        data = request.json
        message = data.get('message', '')
        document_type = data.get('document_type', 'general')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Extract user data
        user_data = extract_user_data(message)
        
        # Generate AI response
        ai_response = generate_ai_response(message, document_type)
        
        # Generate PDF
        doc_title = DOCUMENT_TYPES.get(document_type, "AI-Generated Document")
        pdf_path = DocumentGenerator.generate_pdf(ai_response, doc_title, user_data)
        
        # Generate unique filename
        filename = f"{document_type}_{uuid.uuid4().hex[:8]}.pdf"
        
        return jsonify({
            'response': ai_response,
            'pdf_path': pdf_path,
            'filename': filename,
            'document_type': document_type,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Document generation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<path:filepath>')
def download_file(filepath):
    try:
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
        else:
            logger.error(f"File not found: {filepath}")
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)