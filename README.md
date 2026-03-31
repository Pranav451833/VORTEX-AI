# HumanTalk Chatbot

A responsive chatbot web app that can:
- chat in a human-like style
- provide live weather forecasts
- fetch recent news headlines
- answer programming questions with code
- share health tips (general wellness only)

## Run

```bash
pip install -r requirements.txt
python app.py
```

Open: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Ollama Setup

For full local coding answers without any API key, install Ollama and pull a coding model.

1. Install Ollama from [https://ollama.com/download](https://ollama.com/download)
2. Pull a model:

```bash
ollama pull qwen2.5-coder
```

3. Keep Ollama running, then start the Flask app:

```bash
python app.py
```

The chatbot will call Ollama at `http://127.0.0.1:11434` by default.

## Optional Environment Variables

Use a different local model:

```bash
setx OLLAMA_MODEL "deepseek-coder"
```

Use a different Ollama server URL:

```bash
setx OLLAMA_BASE_URL "http://127.0.0.1:11434"
```

Gemini is still supported as a secondary fallback if you add `GEMINI_API_KEY`.
