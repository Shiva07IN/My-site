# AI Document Assistant

A modern web-based AI document generator that creates professional documents using artificial intelligence.

## Features

- **AI-Powered Generation**: Uses Groq API for intelligent document creation
- **Modern Web Interface**: Responsive design with animations and effects
- **Multiple Document Types**: Affidavits, letters, contracts, certificates, applications
- **PDF Export**: Professional PDF generation with proper formatting
- **Mobile Friendly**: Optimized for all devices
- **Real-time Chat**: Interactive AI chat interface

## Live Demo

🌐 **[Try it live on Railway](https://your-app-name.up.railway.app)**

## Quick Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

## Local Setup

1. Clone repository:
   ```bash
   git clone https://github.com/yourusername/ai-document-assistant.git
   cd ai-document-assistant
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   # Create .env file
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. Run application:
   ```bash
   python app.py
   ```

5. Open http://localhost:5000

## Railway Deployment

1. Fork this repository
2. Connect to [Railway](https://railway.app)
3. Set `GROQ_API_KEY` environment variable
4. Deploy automatically

## API Endpoints

- `GET /` - Web interface
- `POST /api/chat` - Chat with AI
- `POST /api/generate-document` - Generate PDF
- `GET /health` - Health check

## Tech Stack

- **Backend**: Flask, Python
- **Frontend**: HTML5, CSS3, JavaScript
- **AI**: Groq API
- **PDF**: ReportLab
- **Deployment**: Railway

## License

MIT
