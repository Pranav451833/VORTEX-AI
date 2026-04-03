import os
import random
import re
import logging
from datetime import datetime
from html import unescape
from typing import Dict, Optional, Tuple
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests
from flask import Flask, jsonify, request, send_from_directory

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

app = Flask(__name__, static_folder="static")
logging.basicConfig(level=logging.INFO)

REQUEST_TIMEOUT = 8
OLLAMA_TIMEOUT = 120
DEFAULT_LOCATION = "New Delhi"
LEETCODE_API_ALL = "https://leetcode.com/api/problems/all/"
LEETCODE_GRAPHQL = "https://leetcode.com/graphql"

HUMAN_OPENERS = [
    "Good one. Here's what I found:",
    "Nice question. Let me help:",
    "Sure, here's a clear answer:",
    "Absolutely. Here's the best way:",
]

HEALTH_TIPS = [
    "Sleep 7-9 hours regularly; consistent sleep improves mood, focus, and immunity.",
    "Aim for a plate split: half vegetables, quarter protein, quarter whole grains.",
    "Walk at least 30 minutes most days; short walks after meals help blood sugar.",
    "Hydrate through the day; a simple target is clear to pale-yellow urine.",
    "Do 2-3 strength sessions weekly to support joints, bones, and metabolism.",
]

EMERGENCY_KEYWORDS = {
    "chest pain",
    "difficulty breathing",
    "fainting",
    "stroke",
    "suicidal",
    "severe bleeding",
}

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto")
OPENROUTER_TIMEOUT = 60


def classify_intent(text: str) -> str:
    t = text.lower()
    if re.fullmatch(r"\d{1,4}", t.strip()):
        return "programming"
    if any(x in t for x in ["weather", "forecast", "temperature", "rain"]):
        return "weather"
    if any(x in t for x in ["news", "headline", "latest updates"]):
        return "news"
    if any(
        x in t
        for x in [
            "python",
            "java",
            "javascript",
            "c++",
            "bug",
            "error",
            "code",
            "algorithm",
            "sql",
            "program",
            "leetcode",
            "leet",
            "leet code",
        ]
    ):
        return "programming"
    if any(
        x in t
        for x in [
            "health",
            "diet",
            "fitness",
            "exercise",
            "sleep",
            "wellness",
            "blood pressure",
            "tips",
        ]
    ):
        return "health"
    return "chat"


def extract_location(text: str) -> str:
    match = re.search(r"(?:in|at|for)\s+([a-zA-Z\s,]+)", text.lower())
    if match:
        return match.group(1).strip(" ?.,").title()
    return DEFAULT_LOCATION


def extract_topic(text: str) -> str:
    lowered = text.lower()
    topic = lowered.replace("news", "").replace("about", "").strip(" ?.,")
    return topic if topic else "world"


def geocode_city(city: str) -> Tuple[float, float, str]:
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote_plus(city)}&count=1"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    results = data.get("results") or []
    if not results:
        raise ValueError("Location not found")
    first = results[0]
    return first["latitude"], first["longitude"], first["name"]


def get_weather_summary(city: str) -> str:
    try:
        lat, lon, normalized = geocode_city(city)
        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,weather_code,wind_speed_10m"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&timezone=auto"
        )
        response = requests.get(weather_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        t_max = daily.get("temperature_2m_max", [])
        t_min = daily.get("temperature_2m_min", [])
        rain = daily.get("precipitation_probability_max", [])

        lines = [
            f"Forecast for {normalized}:",
            f"Now: {current.get('temperature_2m', 'N/A')} C, wind {current.get('wind_speed_10m', 'N/A')} km/h.",
        ]

        for i in range(min(3, len(dates))):
            day = datetime.fromisoformat(dates[i]).strftime("%a")
            lines.append(
                f"{day}: {t_min[i]} C to {t_max[i]} C, rain chance ~{rain[i]}%.")

        lines.append("Weather can change fast, so check again before travel.")
        return "\n".join(lines)
    except Exception:
        return "I couldn't fetch live weather right now. Try: 'weather in Mumbai'."


def get_news_summary(topic: str) -> str:
    try:
        rss_url = f"https://news.google.com/rss/search?q={quote_plus(topic)}"
        response = requests.get(rss_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items = root.findall("./channel/item")[:5]

        if not items:
            return f"I couldn't find headlines for '{topic}' right now."

        lines = [f"Top headlines on {topic}:"]
        for idx, item in enumerate(items, start=1):
            title = unescape((item.findtext("title") or "").strip())
            lines.append(f"{idx}. {title}")

        lines.append(
            "If you want, ask: 'news about AI' or 'news about cricket'.")
        return "\n".join(lines)
    except Exception:
        return "News service is temporarily unavailable. Try again in a moment."


def detect_requested_language(user_text: str) -> str:
    lower = user_text.lower()
    if "java" in lower:
        return "Java"
    if "c++" in lower or "cpp" in lower:
        return "C++"
    if "javascript" in lower or "js" in lower:
        return "JavaScript"
    if "typescript" in lower or "ts" in lower:
        return "TypeScript"
    if "python" in lower or "py" in lower:
        return "Python"
    if "c#" in lower or "csharp" in lower:
        return "C#"
    if "go" in lower or "golang" in lower:
        return "Go"
    if "rust" in lower:
        return "Rust"
    if "kotlin" in lower:
        return "Kotlin"
    return "Python"


def normalize_leetcode_language(language: str) -> str:
    mapping = {
        "C#": "Csharp",
        "JavaScript": "JavaScript",
        "TypeScript": "TypeScript",
        "C++": "C++",
        "Python": "Python3",
    }
    return mapping.get(language, language)


def extract_leetcode_number(user_text: str) -> Optional[str]:
    stripped = user_text.strip().lower()
    if re.fullmatch(r"\d{1,4}", stripped):
        return stripped

    match = re.search(r"(?:leetcode|leet|question)\s*#?\s*(\d{1,4})", stripped)
    if match:
        return match.group(1)

    return None


def get_leetcode_problem_slug(question_number: str) -> Optional[str]:
    try:
        response = requests.get(LEETCODE_API_ALL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        for item in data.get("stat_status_pairs", []):
            stat = item.get("stat", {})
            frontend_id = str(stat.get("frontend_question_id", "")).strip()
            if frontend_id == str(question_number):
                return stat.get("question__title_slug")
        return None
    except Exception:
        return None


def get_leetcode_problem_details(title_slug: str) -> Optional[Dict[str, str]]:
    query = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        title
        titleSlug
        content
        difficulty
        exampleTestcases
        codeSnippets {
          lang
          langSlug
          code
        }
      }
    }
    """
    payload = {
        "operationName": "questionData",
        "query": query,
        "variables": {"titleSlug": title_slug},
    }
    try:
        response = requests.post(
            LEETCODE_GRAPHQL, json=payload, timeout=REQUEST_TIMEOUT * 2)
        response.raise_for_status()
        question = (response.json().get("data") or {}).get("question")
        return question if question else None
    except Exception:
        return None


def get_leetcode_code_snippet(details: Dict[str, object], language: str) -> Optional[str]:
    target = normalize_leetcode_language(language).lower()
    for snippet in details.get("codeSnippets", []) or []:
        lang = str(snippet.get("lang", "")).lower()
        lang_slug = str(snippet.get("langSlug", "")).lower()
        if lang == target or lang_slug == target:
            return snippet.get("code")

    # Fallback for common aliases.
    aliases = {
        "python3": {"python", "python3"},
        "csharp": {"c#", "csharp"},
        "javascript": {"javascript", "js"},
        "typescript": {"typescript", "ts"},
        "c++": {"c++", "cpp"},
        "golang": {"go", "golang"},
    }
    valid_aliases = aliases.get(target, {target})
    for snippet in details.get("codeSnippets", []) or []:
        lang = str(snippet.get("lang", "")).lower()
        lang_slug = str(snippet.get("langSlug", "")).lower()
        if lang in valid_aliases or lang_slug in valid_aliases:
            return snippet.get("code")
    return None


def build_leetcode_prompt(user_text: str, language: str) -> Optional[str]:
    question_number = extract_leetcode_number(user_text)
    if not question_number:
        return None

    title_slug = get_leetcode_problem_slug(question_number)
    if not title_slug:
        return None

    details = get_leetcode_problem_details(title_slug)
    if not details:
        return (
            f"Solve LeetCode problem #{question_number} titled '{title_slug.replace('-', ' ')}'. "
            f"Return only the final {language} code in LeetCode submission format."
        )

    title = details.get("title", title_slug.replace("-", " ").title())
    content = unescape(re.sub(r"<[^>]+>", " ", details.get("content", "")))
    content = re.sub(r"\s+", " ", content).strip()
    content = content[:2200]
    example_testcases = (details.get("exampleTestcases") or "").strip()
    example_testcases = example_testcases[:800]
    difficulty = details.get("difficulty", "")
    starter_code = get_leetcode_code_snippet(details, language)

    prompt_parts = [
        f"Solve LeetCode problem #{question_number}: {title}.",
        f"Language: {language}.",
        "Return only the final code in exact LeetCode submission format.",
        "Do not include explanation, comments before code, markdown fences, or example usage unless explicitly requested.",
        "Your output must be directly submittable on LeetCode.",
        "Use the exact class name, method name, parameters, and return type expected by LeetCode.",
    ]

    if difficulty:
        prompt_parts.append(f"Difficulty: {difficulty}.")
    if content:
        prompt_parts.append(f"Problem statement: {content}")
    if example_testcases:
        prompt_parts.append(f"Example testcases: {example_testcases}")
    if starter_code:
        prompt_parts.append(
            "Complete the following official LeetCode starter template."
            " Preserve the outer structure exactly and only fill in the implementation body."
        )
        prompt_parts.append(f"Starter template:\n{starter_code}")
        prompt_parts.append(
            "The first line of your answer must begin with the same declaration as the starter template."
        )
    else:
        prompt_parts.append(
            "If no starter template is available, infer the standard LeetCode submission format for this language."
        )

    return "\n".join(prompt_parts)


def looks_like_valid_leetcode_response(response_text: str, starter_code: str) -> bool:
    response = response_text.strip()
    starter = starter_code.strip()
    if not response or not starter:
        return False

    starter_lines = [line.rstrip()
                     for line in starter.splitlines() if line.strip()]
    response_lines = [line.rstrip()
                      for line in response.splitlines() if line.strip()]
    if not starter_lines or not response_lines:
        return False

    starter_first = starter_lines[0].strip()
    response_first = response_lines[0].strip()
    if starter_first != response_first:
        return False

    if len(starter_lines) > 1:
        starter_second = starter_lines[1].strip()
        if starter_second and not any(line.strip() == starter_second for line in response_lines[:4]):
            return False

    return True


def rewrite_into_leetcode_template(
    raw_response: str,
    starter_code: str,
    language: str,
) -> Tuple[Optional[str], Optional[str]]:
    rewrite_prompt = (
        "Rewrite the candidate solution into exact LeetCode submission format.\n"
        "Return only code.\n"
        "Preserve the official starter template structure exactly.\n"
        "Do not include markdown fences or explanations.\n"
        f"Language: {language}\n\n"
        f"Official starter template:\n{starter_code}\n\n"
        f"Candidate solution:\n{raw_response}"
    )

    if OPENROUTER_API_KEY:
        rewritten, rewrite_error = solve_with_openrouter(rewrite_prompt)
        if rewritten:
            return rewritten, None
        if rewrite_error:
            return None, rewrite_error

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": rewrite_prompt,
        "stream": False,
    }
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        text = (response.json().get("response") or "").strip()
        if text:
            return text, None
        return None, "Template rewrite returned an empty response."
    except requests.RequestException as exc:
        return None, f"Template rewrite failed: {exc}"
    except Exception as exc:
        return None, f"Unexpected template rewrite error: {exc}"


def solve_with_openrouter(prompt: str) -> Tuple[Optional[str], Optional[str]]:
    if not OPENROUTER_API_KEY:
        return None, "OpenRouter API key is not configured."

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a coding assistant. Follow the user's formatting instructions exactly.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1200,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:5000",
        "X-Title": "Vortex AI",
    }
    try:
        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json=payload,
            timeout=OPENROUTER_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return None, "OpenRouter returned no choices."
        message = choices[0].get("message") or {}
        text = (message.get("content") or "").strip()
        if text:
            return text, None
        return None, "OpenRouter returned an empty response."
    except requests.RequestException as exc:
        logging.warning("OpenRouter request failed: %s", exc)
        return None, f"OpenRouter request failed: {exc}"
    except Exception as exc:
        logging.exception("Unexpected OpenRouter error")
        return None, f"Unexpected OpenRouter error: {exc}"


def solve_programming_with_ollama(user_text: str) -> Tuple[Optional[str], Optional[str]]:
    language = detect_requested_language(user_text)
    prompt = build_leetcode_prompt(user_text, language)
    if not prompt:
        prompt = (
            "You are a coding assistant.\n"
            "Return only the final code by default.\n"
            "Do not add explanation, steps, complexity, comments before code, or example usage unless the user explicitly asks.\n"
            f"If the language is unspecified, choose {language}.\n\n"
            f"User request: {user_text}"
        )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        text = (response.json().get("response") or "").strip()
        if text:
            return text, None
        return None, "Ollama returned an empty response."
    except requests.Timeout:
        return None, (
            f"Ollama timed out after {OLLAMA_TIMEOUT} seconds. "
            "The model may still be loading into memory."
        )
    except requests.RequestException as exc:
        return None, f"Ollama request failed: {exc}"
    except Exception as exc:
        return None, f"Unexpected Ollama error: {exc}"


def solve_programming_with_openrouter(user_text: str) -> Tuple[Optional[str], Optional[str]]:
    language = detect_requested_language(user_text)
    prompt = build_leetcode_prompt(user_text, language)
    if not prompt:
        prompt = (
            "You are a coding assistant.\n"
            "Return only the final code by default.\n"
            "Do not add explanation, steps, complexity, comments before code, or example usage unless the user explicitly asks.\n"
            f"If the language is unspecified, choose {language}.\n\n"
            f"User request: {user_text}"
        )
    return solve_with_openrouter(prompt)


def programming_response(user_text: str) -> Tuple[str, str, Optional[str]]:
    language = detect_requested_language(user_text)
    question_number = extract_leetcode_number(user_text)
    generated_answer = None
    generated_error = None
    response_source = "unknown"

    openrouter_answer, openrouter_error = solve_programming_with_openrouter(
        user_text)
    if openrouter_answer:
        generated_answer = openrouter_answer
        response_source = "OpenRouter"
    else:
        if openrouter_error:
            logging.info("Falling back to Ollama because OpenRouter failed: %s", openrouter_error)
        ollama_answer, ollama_error = solve_programming_with_ollama(user_text)
        if ollama_answer:
            generated_answer = ollama_answer
            response_source = "Ollama"
        else:
            generated_error = openrouter_error or ollama_error

    if generated_answer:
        if question_number:
            title_slug = get_leetcode_problem_slug(question_number)
            if title_slug:
                details = get_leetcode_problem_details(title_slug)
                if details:
                    starter_code = get_leetcode_code_snippet(details, language)
                    if starter_code and not looks_like_valid_leetcode_response(generated_answer, starter_code):
                        rewritten, rewrite_error = rewrite_into_leetcode_template(
                            generated_answer,
                            starter_code,
                            language,
                        )
                        if rewritten and looks_like_valid_leetcode_response(rewritten, starter_code):
                            return rewritten, response_source, generated_error
                        if rewrite_error:
                            generated_error = rewrite_error
        return generated_answer, response_source, generated_error

    return (
        f"{random.choice(HUMAN_OPENERS)}\n"
        "I could not generate a code answer.\n"
        f"Details: {generated_error or 'No model response received.'}\n"
        f"OpenRouter model: {OPENROUTER_MODEL}\n"
        f"Ollama model: {OLLAMA_MODEL}",
        "error",
        generated_error,
    )


def health_response(user_text: str) -> str:
    lower = user_text.lower()
    if any(k in lower for k in EMERGENCY_KEYWORDS):
        return (
            "This may be urgent. Please contact local emergency services immediately or go to the nearest ER. "
            "I can only give general wellness information, not emergency care."
        )

    tips = random.sample(HEALTH_TIPS, k=3)
    return (
        "Here are practical health tips:\n"
        f"1. {tips[0]}\n"
        f"2. {tips[1]}\n"
        f"3. {tips[2]}\n"
        "If you have a medical condition, confirm changes with a licensed doctor."
    )


def chat_response(user_text: str) -> str:
    prompts = [
        "I am here with you. Ask me for live weather, latest news, coding help, or health tips.",
        "Let's chat. You can ask things like 'weather in Delhi' or 'debug this Python code'.",
        "Happy to help. I can answer naturally and switch between news, weather, coding, and wellness.",
    ]
    if re.search(r"\b(hi|hello|hey)\b", user_text.lower()):
        return "Hey! Nice to meet you. What should we start with today?"
    return random.choice(prompts)


@app.get("/")
def index() -> object:
    return send_from_directory("static", "index.html")


@app.post("/chat")
def chat() -> object:
    payload: Dict[str, str] = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()

    if not message:
        return jsonify({"response": "Send a message and I will jump in."}), 400

    intent = classify_intent(message)

    if intent == "weather":
        response = get_weather_summary(extract_location(message))
        source = "weather"
        source_detail = None
    elif intent == "news":
        response = get_news_summary(extract_topic(message))
        source = "news"
        source_detail = None
    elif intent == "programming":
        response, source, source_detail = programming_response(message)
    elif intent == "health":
        response = health_response(message)
        source = "health"
        source_detail = None
    else:
        response = chat_response(message)
        source = "chat"
        source_detail = None

    return jsonify({"response": response, "intent": intent, "source": source, "source_detail": source_detail})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
