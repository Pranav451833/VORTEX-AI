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

## OpenRouter Setup

For public-friendly code generation, configure an OpenRouter API key:

```bash
setx OPENROUTER_API_KEY "your_key_here"
```

You can also place the key in a local `.env` file as `OPENROUTER_API_KEY=...`.

Optional model override:

```bash
setx OPENROUTER_MODEL "deepseek/deepseek-chat-v3-0324:free"
```

Then restart terminal and run:

```bash
python app.py
```

## Ollama Setup

Ollama is still supported as a local fallback if OpenRouter is unavailable.

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
