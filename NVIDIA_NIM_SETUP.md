# NVIDIA NIM API Integration

## Model Selection
**Selected Model**: `meta/llama-3.1-70b-instruct`

### Why This Model?
- **Best for document generation**: Excellent at structured content
- **High quality**: 70B parameters for superior output
- **Instruction following**: Perfect for document templates
- **Professional formatting**: Handles legal/business documents well

## Railway Environment Variable
Add this to your Railway project:

```
NVIDIA_API_KEY=your_nvidia_api_key_here
```

## API Configuration
- **Base URL**: `https://integrate.api.nvidia.com/v1`
- **Model**: `meta/llama-3.1-70b-instruct`
- **Endpoint**: `/chat/completions`

## Features
- ✅ OpenAI-compatible API format
- ✅ Better document generation than Groq
- ✅ Higher token limits (4000 for documents)
- ✅ Professional error handling
- ✅ Timeout protection (30s)

## Usage
1. Get your NVIDIA API key from NVIDIA NIM
2. Add `NVIDIA_API_KEY` to Railway environment variables
3. Deploy your app
4. Test document generation

Your AI Document Assistant now uses NVIDIA's powerful Llama 3.1 70B model!