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
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
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
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                textColor=colors.black
            )
            
            content_style = ParagraphStyle(
                'ContentStyle',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=12,
                leading=16,
                fontName='Helvetica',
                textColor=colors.black,
                alignment=TA_LEFT
            )
            
            signature_style = ParagraphStyle(
                'SignatureStyle',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                fontName='Helvetica',
                alignment=TA_RIGHT
            )
            
            elements = []
            
            # Add title
            elements.append(Paragraph(title.upper(), title_style))
            elements.append(Spacer(1, 20))
            
            # Add date
            current_date = datetime.now().strftime("%d/%m/%Y")
            elements.append(Paragraph(f"<b>Date:</b> {current_date}", content_style))
            elements.append(Spacer(1, 20))
            
            # Process and add main content
            clean_text = str(text).replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            
            # Split content into paragraphs and format
            paragraphs = clean_text.split('\n')
            for para in paragraphs:
                if para.strip():
                    elements.append(Paragraph(para.strip(), content_style))
                    elements.append(Spacer(1, 8))
            
            # Add signature section
            elements.append(Spacer(1, 30))
            elements.append(Paragraph("_" * 30, signature_style))
            elements.append(Paragraph("Signature", signature_style))
            
            doc.build(elements)
            return filepath
            
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            raise e

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

async def generate_ai_response(prompt: str, document_type: str) -> str:
    """Generate AI response using Groq API"""
    if not groq_client:
        return "AI service not available. Please check configuration."
    
    try:
        system_prompts = {
            'affidavit': "You are an expert legal document writer. Create a complete, professional affidavit with proper legal format.",
            'letter': "You are a professional business letter writer. Create a complete formal letter with proper format.",
            'contract': "You are a contract specialist. Create a comprehensive contract with clear terms.",
            'certificate': "You are creating official certificates. Generate a formal certificate with proper formatting.",
            'application': "You are an expert in applications. Create authentic applications with proper format.",
            'general': "You are a professional assistant. Provide helpful, well-structured responses."
        }
        
        system_prompt = system_prompts.get(document_type, system_prompts['general'])
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a {document_type} based on: {prompt}"}
            ],
            model="llama3-70b-8192",
            temperature=0.3,
            max_tokens=2000
        )
        
        return chat_completion.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return f"AI service error: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        document_type = data.get('document_type', 'general')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Generate AI response
        ai_response = generate_ai_response(message, document_type)
        
        return jsonify({
            'response': ai_response,
            'document_type': document_type,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500

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
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)