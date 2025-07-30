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
    """Generate AI response using Groq API with advanced prompting"""
    if not groq_client:
        if not GROQ_API_KEY:
            return "❌ GROQ_API_KEY not found. Please add it in Railway Variables."
        return "❌ AI service not available. Please check configuration."
    
    try:
        # Advanced system prompts with detailed instructions
        system_prompts = {
            'affidavit': """You are a senior legal document specialist with 20+ years experience. Create a legally compliant affidavit with:
            
STRUCTURE:
            1. AFFIDAVIT title (centered, bold)
            2. STATE/JURISDICTION line
            3. COUNTY line  
            4. Declarant identification (I, [NAME], being duly sworn...)
            5. Numbered factual statements (clear, specific)
            6. Oath clause ("I declare under penalty of perjury...")
            7. Signature block with notary section
            
            LANGUAGE: Formal legal terminology, first person, present tense for facts
            FORMAT: Professional legal document structure with proper spacing""",
            
            'letter': """You are an executive communications expert. Create a professional business letter with:
            
            STRUCTURE:
            1. Sender's address (top right or letterhead)
            2. Date
            3. Recipient's address (left aligned)
            4. Subject line (RE: [SUBJECT])
            5. Professional salutation (Dear Mr./Ms. [NAME])
            6. Opening paragraph (purpose)
            7. Body paragraphs (details, supporting information)
            8. Closing paragraph (call to action/next steps)
            9. Professional closing (Sincerely, Best regards)
            10. Signature block
            
            TONE: Professional, courteous, clear and concise
            FORMAT: Standard business letter format with proper spacing""",
            
            'contract': """You are a contract law specialist. Create a comprehensive legal contract with:
            
            STRUCTURE:
            1. CONTRACT TITLE (specific type)
            2. PARTIES section (full legal names, addresses)
            3. RECITALS ("WHEREAS" clauses)
            4. TERMS AND CONDITIONS (numbered articles)
            5. PAYMENT TERMS (amounts, schedules, methods)
            6. DURATION AND TERMINATION
            7. OBLIGATIONS OF EACH PARTY
            8. DISPUTE RESOLUTION
            9. GOVERNING LAW
            10. SIGNATURE BLOCKS with witness lines
            
            LANGUAGE: Precise legal terminology, "shall" for obligations
            FORMAT: Professional contract structure with clear sections""",
            
            'certificate': """You are an official certification authority. Create a formal certificate with:
            
            STRUCTURE:
            1. CERTIFICATE OF [TYPE] (centered, prominent)
            2. Official seal/logo placeholder
            3. "This is to certify that" statement
            4. Recipient name (prominent, centered)
            5. Achievement/completion details
            6. Date of completion/achievement
            7. Issuing authority information
            8. Authorized signature block
            9. Official seal placement
            
            TONE: Formal, official, authoritative
            FORMAT: Certificate layout with centered elements""",
            
            'application': """You are an application processing expert. Create a complete application form with:
            
            STRUCTURE:
            1. APPLICATION FOR [PURPOSE] (title)
            2. APPLICANT INFORMATION (personal details)
            3. APPLICATION DETAILS (specific requirements)
            4. SUPPORTING INFORMATION (qualifications, reasons)
            5. DECLARATIONS (truthfulness, compliance)
            6. REQUIRED DOCUMENTS (checklist)
            7. SIGNATURE AND DATE
            8. FOR OFFICE USE ONLY (processing section)
            
            TONE: Formal, respectful, complete
            FORMAT: Standard application form structure""",
            
            'general': """You are a professional document specialist. Create well-structured documents with:
            - Clear hierarchical headings
            - Logical flow and organization
            - Professional language appropriate to document type
            - Complete sections with all necessary elements
            - Proper formatting and spacing"""
        }
        
        system_prompt = system_prompts.get(document_type, system_prompts['general'])
        
        # Enhanced user prompt with specific formatting instructions
        user_prompt = f"""Create a professional {document_type.upper()} document based on this request:
        
        REQUEST: {prompt}
        
        CRITICAL FORMATTING REQUIREMENTS:
        ✓ Use UPPERCASE for all section headings
        ✓ Use numbered points (1., 2., 3.) for lists
        ✓ Include placeholder fields: [NAME], [ADDRESS], [DATE], [AMOUNT], etc.
        ✓ Add proper spacing between sections
        ✓ Use formal, professional language
        ✓ Include all legally required elements
        ✓ Make document complete and ready for use
        ✓ Add signature lines and date fields
        ✓ Include any necessary legal disclaimers
        
        OUTPUT: A complete, professional document that can be immediately used."""
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama3-70b-8192",
            temperature=0.1,  # Lower for more consistent output
            max_tokens=4000,  # Increased for longer documents
            top_p=0.9,
            frequency_penalty=0.1
        )
        
        response = chat_completion.choices[0].message.content.strip()
        
        # Post-process response for better formatting
        response = response.replace('**', '').replace('*', '')  # Remove markdown
        response = re.sub(r'\n{3,}', '\n\n', response)  # Normalize spacing
        
        return response
        
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        error_msg = str(e)
        if "json" in error_msg.lower():
            return "❌ API response format error. Please try again."
        elif "rate limit" in error_msg.lower():
            return "❌ Rate limit exceeded. Please wait and try again."
        elif "invalid" in error_msg.lower():
            return "❌ Invalid API key. Please check your GROQ_API_KEY."
        elif "timeout" in error_msg.lower():
            return "❌ Request timeout. Please try again."
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
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        message = data.get('message', '').strip()
        document_type = data.get('document_type', 'general')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        if len(message) < 10:
            return jsonify({'error': 'Please provide more details for better document generation'}), 400
        
        # Extract user data
        user_data = extract_user_data(message)
        
        # Generate AI response
        ai_response = generate_ai_response(message, document_type)
        
        # Check if AI response is an error
        if ai_response.startswith('❌'):
            return jsonify({
                'error': ai_response,
                'status': 'error'
            }), 400
        
        # Generate PDF
        doc_title = DOCUMENT_TYPES.get(document_type, "AI-Generated Document")
        
        try:
            pdf_path = DocumentGenerator.generate_pdf(ai_response, doc_title, user_data)
        except Exception as pdf_error:
            logger.error(f"PDF generation failed: {pdf_error}")
            return jsonify({
                'error': 'PDF generation failed. Please try again.',
                'status': 'error'
            }), 500
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{document_type}_{timestamp}.pdf"
        
        return jsonify({
            'response': ai_response,
            'pdf_path': pdf_path,
            'filename': filename,
            'document_type': document_type,
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Document generation error: {e}")
        return jsonify({
            'error': f'Document generation failed: {str(e)}',
            'status': 'error'
        }), 500

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