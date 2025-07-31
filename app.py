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
import requests
import json
import re
import tempfile
import uuid
import threading
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
PORT = int(os.getenv('PORT', 5000))

# NVIDIA NIM Configuration
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL = "sarvam/sarvam-2b-v0-5"  # Sarvam-M AI for Indian context

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    def cleanup_old_files():
        """Clean up PDF files older than 1 hour"""
        try:
            temp_dir = tempfile.gettempdir()
            current_time = time.time()
            
            for filename in os.listdir(temp_dir):
                if filename.startswith('doc_') and filename.endswith('.pdf'):
                    filepath = os.path.join(temp_dir, filename)
                    try:
                        file_age = current_time - os.path.getctime(filepath)
                        if file_age > 3600:  # 1 hour
                            os.remove(filepath)
                            logger.info(f"Cleaned up old PDF: {filepath}")
                    except Exception as e:
                        logger.warning(f"Could not clean up {filepath}: {e}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    @staticmethod
    def clean_text_for_pdf(text: str) -> str:
        """Clean and prepare text for PDF generation"""
        if not text:
            return ""
        
        # Remove HTML tags and entities
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        text = text.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&#39;', "'")
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Escape special characters for ReportLab
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        return text.strip()
    
    @staticmethod
    def generate_pdf(text: str, title: str, user_data: dict) -> str:
        try:
            # Validate input
            if not text or not text.strip():
                raise ValueError("No content provided for PDF generation")
            
            if not title or not title.strip():
                title = "AI Generated Document"
            
            # Clean text
            clean_text = DocumentGenerator.clean_text_for_pdf(text)
            if not clean_text:
                raise ValueError("Content is empty after cleaning")
            
            # Create secure temporary file
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"doc_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
            filepath = os.path.join(temp_dir, filename)
            
            logger.info(f"Creating PDF: {filename}")
            
            # Create PDF document
            doc = SimpleDocTemplate(
                filepath, 
                pagesize=A4,
                rightMargin=60, leftMargin=60,
                topMargin=60, bottomMargin=60
            )
            
            # Define styles
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Title'],
                fontSize=18,
                spaceAfter=24,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            heading_style = ParagraphStyle(
                'Heading',
                parent=styles['Heading2'],
                fontSize=13,
                spaceAfter=12,
                spaceBefore=16,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'Normal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=12,
                leading=16,
                fontName='Helvetica'
            )
            
            signature_style = ParagraphStyle(
                'Signature',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=8,
                alignment=TA_RIGHT,
                fontName='Helvetica'
            )
            
            # Build document elements
            elements = []
            
            # Title
            elements.append(Paragraph(title.upper(), title_style))
            elements.append(Spacer(1, 20))
            
            # Date
            current_date = datetime.now().strftime("%B %d, %Y")
            elements.append(Paragraph(f"<b>Date:</b> {current_date}", normal_style))
            elements.append(Spacer(1, 16))
            
            # Process content
            paragraphs = clean_text.split('\n')
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    elements.append(Spacer(1, 6))
                    continue
                
                # Detect headings
                is_heading = (
                    para.isupper() and len(para) < 60 or
                    para.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or
                    para.startswith(('To,', 'Subject:', 'DEPONENT', 'VERIFICATION', 'WHEREAS'))
                )
                
                if is_heading:
                    elements.append(Paragraph(para, heading_style))
                else:
                    elements.append(Paragraph(para, normal_style))
                    
                    # Extra spacing after certain phrases
                    if any(phrase in para.lower() for phrase in ['sincerely', 'faithfully', 'regards']):
                        elements.append(Spacer(1, 16))
            
            # Signature section
            elements.append(Spacer(1, 30))
            elements.append(Paragraph("_" * 35, signature_style))
            elements.append(Paragraph("Signature & Date", signature_style))
            
            # Build PDF
            doc.build(elements)
            
            # Verify creation
            if not os.path.exists(filepath):
                raise RuntimeError("PDF file was not created")
            
            file_size = os.path.getsize(filepath)
            if file_size == 0:
                raise RuntimeError("Generated PDF is empty")
            
            logger.info(f"PDF created successfully: {file_size} bytes")
            
            # Background cleanup
            threading.Thread(
                target=DocumentGenerator.cleanup_old_files,
                daemon=True
            ).start()
            
            return filepath
            
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise RuntimeError(f"PDF generation error: {str(e)}")

def extract_user_data(text: str) -> dict:
    """Extract user data from text"""
    if not text:
        return {}
    
    data = {}
    text_lower = text.lower()
    
    # Name patterns (fixed regex)
    name_patterns = [
        r"(?:my name is|i am|name:?)\s*([A-Za-z\s]+)",
        r"([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
    ]
    
    # Address patterns (fixed regex)
    address_patterns = [
        r"(?:address|live at|residing at|from):?\s*([^.\n]+(?:\d{6}|\d{3}\s*\d{3})[^.\n]*)"
    ]
    
    # Extract name
    for pattern in name_patterns:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and len(match.group(1).strip().split()) >= 2:
                data['full_name'] = match.group(1).strip()
                break
        except Exception:
            continue
    
    # Extract address
    for pattern in address_patterns:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['address'] = match.group(1).strip()
                break
        except Exception:
            continue
    
    return data

class IndianDocumentAgent:
    """Advanced AI agent specialized for Indian document generation"""
    
    def __init__(self):
        self.indian_legal_terms = {
            'deponent': 'the person making the affidavit',
            'verification': 'legal confirmation of truth',
            'whereas': 'legal preamble clause',
            'hereby': 'by this document',
            'aforesaid': 'mentioned before'
        }
        
        self.indian_formats = {
            'date_format': '%d/%m/%Y',
            'address_pattern': r'([A-Za-z0-9\s,.-]+)[-\s]*([1-9][0-9]{5})$',
            'name_pattern': r'^[A-Za-z\s.]+$'
        }
    
    def get_system_prompt(self, doc_type: str) -> str:
        """Get refined system prompt for Indian documents"""
        prompts = {
            'affidavit': """You are an expert Indian legal document specialist with 20+ years experience. Create PERFECT Indian affidavits following Supreme Court guidelines.

CRITICAL REQUIREMENTS:
✓ Use EXACT Indian legal format and terminology
✓ Include proper verification clause as per Indian Evidence Act
✓ Use "son/daughter of" format (not "s/o" or "d/o")
✓ Include complete address with PIN code
✓ Use formal legal language with "That" clauses
✓ Add proper deponent signature blocks
✓ Include notarization space

STRUCTURE:
AFFIDAVIT

I, [FULL NAME], son/daughter of [FATHER'S NAME], aged [AGE] years, resident of [COMPLETE ADDRESS WITH PIN], do hereby solemnly affirm and declare as under:

1. That I am the deponent herein and competent to swear to this affidavit.
2. That [MAIN STATEMENT with specific details].
3. That [SUPPORTING FACTS with evidence].
4. That [ADDITIONAL CLAUSES as needed].
5. That I undertake to inform concerned authorities if any information is found false.
6. That this affidavit is made for [SPECIFIC PURPOSE] only.

DEPONENT

VERIFICATION
I, the above-named deponent, verify that contents are true to my knowledge and belief, nothing material concealed.

Verified at [PLACE] on [DATE].

DEPONENT

Before me:
Notary Public/Oath Commissioner""",

            'letter': """You are a senior Indian business communication expert. Create PERFECT Indian business letters following government and corporate standards.

CRITICAL REQUIREMENTS:
✓ Use proper Indian business letter format
✓ Include complete sender details with PIN code
✓ Use respectful Indian business language
✓ Add proper subject line format
✓ Include reference numbers if applicable
✓ Use "Yours faithfully" for unknown recipients, "Yours sincerely" for known
✓ Add enclosure list if documents attached

STRUCTURE:
[SENDER NAME]
[DESIGNATION]
[ORGANIZATION]
[COMPLETE ADDRESS]
[CITY - PIN CODE]
[EMAIL] | [MOBILE]

Ref: [REFERENCE NUMBER]
Date: [DD/MM/YYYY]

To,
[RECIPIENT NAME]
[DESIGNATION]
[ORGANIZATION]
[COMPLETE ADDRESS]
[CITY - PIN CODE]

Subject: [CLEAR SUBJECT LINE]

Dear Sir/Madam,

I hope this letter finds you in good health.

[OPENING PARAGRAPH - Purpose]
[MAIN CONTENT - Details with bullet points if needed]
[CLOSING PARAGRAPH - Action requested]

I shall be grateful for your kind consideration and early response.

Thanking you,

Yours faithfully/sincerely,

[SIGNATURE]
[FULL NAME]
[DESIGNATION]

Enclosures: [LIST IF ANY]""",

            'application': """You are an expert Indian government application specialist with deep knowledge of both English and Hindi official formats. You have 25+ years experience in Indian bureaucracy and understand regional preferences.

CRITICAL REQUIREMENTS:
✓ DETECT LANGUAGE: If user mentions Hindi/हिंदी or uses Hindi words, create Hindi application
✓ Use exact Indian government format for both English and Hindi
✓ Include all mandatory personal details in appropriate language
✓ Use respectful government tone (आदरणीय for Hindi, Respected for English)
✓ Add proper enclosure list in respective language
✓ Include declaration clause for truthfulness
✓ Use correct closing (धन्यवाद सहित for Hindi, Yours faithfully for English)

ENGLISH FORMAT:
To,
[OFFICER DESIGNATION]
[DEPARTMENT/OFFICE]
[COMPLETE ADDRESS]
[CITY - PIN CODE]

Subject: Application for [SPECIFIC PURPOSE]

Respected Sir/Madam,

I, [FULL NAME], son/daughter of [FATHER'S NAME], aged [AGE] years, resident of [ADDRESS], would like to submit this application for [PURPOSE].

My details are as follows:
1. Full Name: [NAME]
2. Father's/Husband's Name: [NAME]
3. Date of Birth: [DD/MM/YYYY]
4. Address: [COMPLETE ADDRESS WITH PIN]
5. Mobile Number: [10-DIGIT NUMBER]
6. Email ID: [EMAIL]
7. Educational Qualification: [DETAILS]

I hereby declare that all information provided is true and correct.

I request you to kindly consider my application favorably. I shall be highly obliged.

Thanking you,
Yours faithfully,

[SIGNATURE]
[FULL NAME]
Date: [DD/MM/YYYY]
Place: [CITY NAME]

Enclosures:
1. [DOCUMENT 1]
2. [DOCUMENT 2]

HINDI FORMAT:
सेवा में,
[अधिकारी पदनाम]
[विभाग/कार्यालय]
[पूरा पता]
[शहर - पिन कोड]

विषय: [विशिष्ट उद्देश्य] हेतु आवेदन पत्र

आदरणीय महोदय/महोदया,

मैं [पूरा नाम], पुत्र/पुत्री श्री [पिता का नाम], आयु [आयु] वर्ष, निवासी [पूरा पता], आपके समक्ष [उद्देश्य] हेतु यह आवेदन पत्र प्रस्तुत कर रहा/रही हूँ।

मेरा विवरण निम्नलिखित है:
1. पूरा नाम: [नाम]
2. पिता/पति का नाम: [नाम]
3. जन्म तिथि: [DD/MM/YYYY]
4. पता: [पूरा पता पिन कोड सहित]
5. मोबाइल नंबर: [10 अंकीय नंबर]
6. ईमेल आईडी: [ईमेल]
7. शैक्षणिक योग्यता: [विवरण]

[मुख्य अनुरोध पैराग्राफ औचित्य सहित]

मैं घोषणा करता/करती हूँ कि उपरोक्त सभी जानकारी सत्य एवं सही है।

अतः आपसे विनम्र निवेदन है कि मेरे आवेदन पर कृपया विचार करें। मैं आपका/आपकी अत्यंत आभारी रहूंगा/रहूंगी।

धन्यवाद सहित,
आपका/आपकी विश्वासपात्र,

[हस्ताक्षर]
[पूरा नाम]
दिनांक: [DD/MM/YYYY]
स्थान: [शहर का नाम]

संलग्नक:
1. [दस्तावेज 1]
2. [दस्तावेज 2]

USE APPROPRIATE FORMAT BASED ON USER'S LANGUAGE PREFERENCE OR REQUEST.""",

            'contract': """You are an Indian contract law expert. Create LEGALLY SOUND contracts following Indian Contract Act 1872.

CRITICAL REQUIREMENTS:
✓ Follow Indian Contract Act provisions
✓ Include proper parties identification
✓ Add consideration clause
✓ Include jurisdiction and governing law
✓ Add dispute resolution mechanism
✓ Include termination clauses
✓ Add witness signatures

STRUCTURE:
[CONTRACT TYPE]

This Agreement is made on [DATE] between:

PARTY 1: [FULL DETAILS]
PARTY 2: [FULL DETAILS]

WHEREAS [RECITALS]

NOW THEREFORE, parties agree:

1. SCOPE OF WORK/SERVICE
2. CONSIDERATION AND PAYMENT
3. DURATION AND COMMENCEMENT
4. OBLIGATIONS OF PARTIES
5. TERMINATION CONDITIONS
6. DISPUTE RESOLUTION
7. GOVERNING LAW
8. MISCELLANEOUS

IN WITNESS WHEREOF, parties execute this agreement.

PARTY 1: ________________
WITNESS: ________________

PARTY 2: ________________
WITNESS: ________________""",

            'certificate': """You are an Indian certification authority expert. Create OFFICIAL certificates following government standards.

CRITICAL REQUIREMENTS:
✓ Use official certificate format
✓ Include proper authority details
✓ Add certificate number and date
✓ Include official seal placement
✓ Use formal certification language
✓ Add validity period if applicable

STRUCTURE:
[ORGANIZATION LETTERHEAD]

CERTIFICATE OF [TYPE]
Certificate No: [NUMBER]
Date: [DD/MM/YYYY]

This is to certify that [RECIPIENT NAME], son/daughter of [FATHER'S NAME], has successfully [ACHIEVEMENT/COMPLETION].

[DETAILED DESCRIPTION]

This certificate is issued on [DATE] and is valid [VALIDITY PERIOD].

[AUTHORIZED SIGNATURE]
[NAME AND DESIGNATION]
[OFFICIAL SEAL]"""
        }
        return prompts.get(doc_type, "You are a helpful AI assistant.")
    
    def validate_indian_content(self, content: str, doc_type: str) -> str:
        """Validate and enhance Indian document content for both English and Hindi"""
        # Detect if content is in Hindi
        hindi_chars = re.findall(r'[\u0900-\u097F]', content)
        is_hindi = len(hindi_chars) > 10
        
        # Add Indian-specific validations
        if doc_type == 'affidavit' and 'VERIFICATION' not in content and 'सत्यापन' not in content:
            if is_hindi:
                content += "\n\nसत्यापन\n\nमैं सत्यापित करता/करती हूँ कि उपरोक्त विवरण मेरी जानकारी के अनुसार सत्य है।\n\nशपथकर्ता"
            else:
                content += "\n\nVERIFICATION\n\nI verify that the contents are true to my knowledge.\n\nDEPONENT"
        
        # Ensure proper Indian address format
        content = re.sub(r'\b(\d{6})\b', r'- \1', content)  # Add dash before PIN
        
        # Fix Indian name formats for English content
        if not is_hindi:
            content = re.sub(r'\bs/o\b', 'son of', content, flags=re.IGNORECASE)
            content = re.sub(r'\bd/o\b', 'daughter of', content, flags=re.IGNORECASE)
        
        # Enhanced application-specific validations
        if doc_type == 'application':
            if is_hindi:
                # Hindi application enhancements
                if 'आदरणीय महोदय' not in content and 'आदरणीय महोदया' not in content:
                    content = content.replace('महोदय', 'आदरणीय महोदय')
                
                # Add declaration if missing in Hindi
                if 'घोषणा करता' not in content and 'घोषणा करती' not in content:
                    declaration = "\n\nमैं घोषणा करता/करती हूँ कि उपरोक्त सभी जानकारी सत्य एवं सही है।"
                    content = content.replace('अतः आपसे विनम्र निवेदन', declaration + '\n\nअतः आपसे विनम्र निवेदन')
                
                # Ensure proper Hindi closing
                if 'धन्यवाद सहित' not in content:
                    content = content.replace('आभारी रहूंगा', 'आभारी रहूंगा।\n\nधन्यवाद सहित,')
            else:
                # English application enhancements
                if 'Respected Sir/Madam' not in content:
                    content = content.replace('Dear Sir/Madam', 'Respected Sir/Madam')
                
                # Add declaration if missing in English
                if 'declare that all the information' not in content.lower():
                    declaration = "\n\nI hereby declare that all the information provided above is true and correct to the best of my knowledge."
                    content = content.replace('I request you to kindly', declaration + '\n\nI request you to kindly')
                
                # Ensure proper English closing
                if 'Yours faithfully' not in content and 'Yours sincerely' not in content:
                    content = content.replace('Thanking you,', 'Thanking you,\n\nYours faithfully,')
        
        return content

def generate_ai_response(prompt: str, document_type: str) -> str:
    """Generate AI response using NVIDIA NIM API with Indian document agent"""
    if not NVIDIA_API_KEY:
        return "❌ NVIDIA_API_KEY not found. Please add it in Railway Variables."
    
    try:
        agent = IndianDocumentAgent()
        system_prompt = agent.get_system_prompt(document_type)
        
        # Enhanced user prompt with Indian context and language detection
        if document_type != 'general':
            if document_type == 'application':
                # Detect Hindi language preference
                hindi_indicators = ['hindi', 'हिंदी', 'हिन्दी', 'देवनागरी', 'भारतीय', 'सरकारी']
                use_hindi = any(indicator in prompt.lower() for indicator in hindi_indicators)
                
                if use_hindi:
                    user_prompt = f"""भारतीय सरकारी कार्यालयों में प्रयुक्त होने वाले सटीक प्रारूप में एक परफेक्ट हिंदी आवेदन पत्र बनाएं।

उपयोगकर्ता का अनुरोध: {prompt}

महत्वपूर्ण आवश्यकताएं:
✓ सटीक भारतीय सरकारी आवेदन प्रारूप का उपयोग करें
✓ सभी अनिवार्य व्यक्तिगत विवरण उचित क्रम में शामिल करें
✓ सम्मानजनक सरकारी संचार भाषा का उपयोग करें
✓ सहायक कारणों के साथ उचित औचित्य जोड़ें
✓ सत्यता के लिए घोषणा खंड शामिल करें
✓ सही भारतीय दिनांक प्रारूप (DD/MM/YYYY) का उपयोग करें
✓ विशिष्ट दस्तावेज़ नामों के साथ पूरी संलग्नक सूची जोड़ें
✓ सरकारी अधिकारियों के लिए "धन्यवाद सहित" समापन का उपयोग करें
✓ सरकारी प्रारूप के अनुसार नीचे दिनांक और स्थान शामिल करें

एक पूर्ण, सरकार-तैयार आवेदन तैयार करें जो तुरंत जमा किया जा सके।"""
                else:
                    user_prompt = f"""Create a PERFECT Indian government application following EXACT official format used in all Indian government offices.

USER REQUEST: {prompt}

CRITICAL REQUIREMENTS:
✓ LANGUAGE DETECTION: Check if user wants Hindi format (look for Hindi words or explicit request)
✓ Use EXACT Indian government application format (English or Hindi as appropriate)
✓ Include ALL mandatory personal details in proper sequence
✓ Use respectful government communication language
✓ Add proper justification with supporting reasons
✓ Include declaration clause for truthfulness
✓ Use correct Indian date format (DD/MM/YYYY)
✓ Add complete enclosure list with specific document names
✓ Use appropriate closing ("Yours faithfully" for English, "धन्यवाद सहित" for Hindi)
✓ Include date and place at bottom as per government format
✓ Ensure document meets all Indian government standards

Generate a COMPLETE, GOVERNMENT-READY application that can be submitted immediately."""
            else:
                user_prompt = f"""Create a professional {document_type.upper()} following EXACT Indian legal/official format.

USER REQUEST: {prompt}

IMPORTANT INSTRUCTIONS:
✓ Use ONLY Indian legal terminology and format
✓ Include ALL mandatory sections and clauses
✓ Use proper Indian address format with PIN codes
✓ Add appropriate legal language and phrases
✓ Include signature blocks and witness lines
✓ Ensure document is legally compliant in India
✓ Use respectful Indian communication style

Generate a COMPLETE, READY-TO-USE document."""
        else:
            user_prompt = f"User question: {prompt}\n\nProvide helpful information about Indian documents or general assistance."
        

        
        # Prepare NVIDIA NIM API request
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Optimized parameters for Sarvam-M AI
        if document_type == 'general':
            payload = {
                "model": NVIDIA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.6,
                "max_tokens": 1500,
                "top_p": 0.85
            }
        elif document_type == 'application':
            # Optimized for Indian government applications
            payload = {
                "model": NVIDIA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2500,
                "top_p": 0.75
            }
        else:
            payload = {
                "model": NVIDIA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 2000,
                "top_p": 0.8
            }
        
        # Make API request
        api_response = requests.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if api_response.status_code != 200:
            raise Exception(f"API request failed: {api_response.status_code} - {api_response.text}")
        
        response_data = api_response.json()
        response = response_data['choices'][0]['message']['content'].strip()
        
        # Post-process with Indian document agent
        if document_type != 'general':
            response = agent.validate_indian_content(response, document_type)
        
        # Clean formatting
        response = response.replace('**', '').replace('*', '')
        response = re.sub(r'\n{3,}', '\n\n', response)
        response = response.replace('\n\n\n', '\n\n')
        
        # Detect language for logging
        hindi_chars = re.findall(r'[\u0900-\u097F]', response)
        language = "Hindi" if len(hindi_chars) > 10 else "English"
        logger.info(f"Sarvam-M generated {document_type} document in {language} with {len(response)} characters")
        
        return response
        
    except requests.exceptions.Timeout:
        logger.error("NVIDIA API timeout")
        return "❌ Request timeout. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error(f"NVIDIA API request error: {e}")
        return "❌ Network error. Please check your connection."
    except Exception as e:
        logger.error(f"NVIDIA API error: {e}")
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return "❌ Invalid API key. Please check your NVIDIA_API_KEY."
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return "❌ Rate limit exceeded. Please wait and try again."
        elif "json" in error_msg.lower():
            return "❌ API response format error. Please try again."
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
        
        if len(message) < 3:
            return jsonify({'error': 'Please provide some details'}), 400
        
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
        
        # Don't generate PDF for general chat
        if document_type == 'general':
            return jsonify({
                'error': 'Please select a document type from dropdown to generate PDF',
                'status': 'error'
            }), 400
        
        # Generate PDF for document types only
        doc_title = DOCUMENT_TYPES.get(document_type, "AI-Generated Document")
        
        try:
            pdf_path = DocumentGenerator.generate_pdf(ai_response, doc_title, user_data)
            
            # Verify PDF creation
            if not pdf_path or not os.path.exists(pdf_path):
                raise RuntimeError("PDF file was not created")
            
            # Verify file size
            if os.path.getsize(pdf_path) == 0:
                raise RuntimeError("Generated PDF is empty")
                
        except (ValueError, RuntimeError) as pdf_error:
            logger.error(f"PDF generation failed: {pdf_error}")
            return jsonify({
                'error': f'PDF generation failed: {str(pdf_error)}',
                'status': 'error'
            }), 500
        except Exception as pdf_error:
            logger.error(f"Unexpected PDF error: {pdf_error}")
            return jsonify({
                'error': 'PDF generation failed. Please try again.',
                'status': 'error'
            }), 500
        
        # Generate clean filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_filename = f"{document_type}_{timestamp}.pdf"
        
        return jsonify({
            'response': ai_response,
            'pdf_path': pdf_path,
            'filename': clean_filename,
            'document_type': document_type,
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'file_size': os.path.getsize(pdf_path)
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
        import urllib.parse
        filepath = urllib.parse.unquote(filepath)
        
        # Validate filepath
        if not filepath or filepath in ['undefined', 'null', '']:
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Security check - ensure file is in temp directory
        temp_dir = tempfile.gettempdir()
        if not filepath.startswith(temp_dir):
            return jsonify({'error': 'Access denied'}), 403
        
        # Check file exists and is readable
        if not (os.path.exists(filepath) and os.path.isfile(filepath) and os.access(filepath, os.R_OK)):
            return jsonify({'error': 'File not found'}), 404
        
        # Validate file size
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        # Generate clean filename
        base_name = os.path.basename(filepath)
        if not base_name.endswith('.pdf'):
            base_name = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        logger.info(f"Serving PDF: {base_name}, size: {file_size} bytes")
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=base_name,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)