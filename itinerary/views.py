from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# -----------------------------
# INDIA-SPECIFIC CONFIG
# -----------------------------

INDIA_INTEREST_MAP = {
    "Temples & Shrines": "temples, shrines, religious sites",
    "Forts & Palaces": "historic forts, palaces, royal heritage",
    "Cultural Heritage": "cultural heritage, traditional arts",
    "Traditional Food": "local cuisine, street food, traditional dishes",
    "Museums & Art Galleries": "museums, art galleries, exhibitions"
}

KNOWN_FREE_PLACES = {
    "Gateway of India",
    "Marine Drive",
    "Juhu Beach",
    "India Gate",
    "Charminar",
    "Howrah Bridge",
    "Rock Beach",
    "Marina Beach",
    "Haji Ali Dargah"
}

BUDGET_CAPS = {
    "Budget Friendly": 2000,
    "Moderate": 5000,
    "Luxury Experience": 12000
}


# -----------------------------
# UTILITY FUNCTIONS
# -----------------------------

def normalize_costs(text):
    for place in KNOWN_FREE_PLACES:
        text = text.replace(f"{place} – Low-cost", f"{place} – Free")
        text = text.replace(f"{place} – Moderate", f"{place} – Free")
        text = text.replace(f"{place} – Premium", f"{place} – Free")
    return text


def enforce_budget_language(text, budget):
    cap = BUDGET_CAPS.get(budget)
    if not cap:
        return text

    if cap <= 2000:
        note = "\n\n📝 Budget Note: Focuses on free attractions, street food, and public transport."
    elif cap <= 5000:
        note = "\n\n📝 Budget Note: Balanced comfort with popular attractions."
    else:
        note = "\n\n📝 Budget Note: Includes premium experiences and flexible spending."

    return text + note


# -----------------------------
# API VIEW
# -----------------------------

@api_view(['POST'])
def generate_itinerary(request):
    """
    Generates a descriptive, budget-safe India itinerary.
    """

    data = request.data

    city = data.get("city")
    location = data.get("location")
    trip_duration = data.get("trip_duration", "1-day")
    budget = data.get("budget", "Moderate")
    interests = data.get("interests", [])

    if not city or not interests:
        return Response(
            {"error": "City and interests are required"},
            status=400
        )

    interest_str = ", ".join(
        INDIA_INTEREST_MAP[i]
        for i in interests
        if i in INDIA_INTEREST_MAP
    )

    location_str = (
        f"The user is currently near {location}. "
        if location else ""
    )

    budget_guidance = {
        "Budget Friendly": "Keep daily spending under ₹2,000 using free attractions and local food.",
        "Moderate": "Spend ₹2,000–₹5,000 per day with comfort and value.",
        "Luxury Experience": "Flexible spending with premium experiences."
    }.get(budget, "")

    # -----------------------------
    # IMPROVED PROMPT (KEY FIX)
    # -----------------------------

    prompt = f"""
You are an expert Indian travel planner and storyteller.

{location_str}
Create a {trip_duration} itinerary for {city}.

User Interests: {interest_str}
Budget Category: {budget}
Budget Guidance: {budget_guidance}

IMPORTANT STYLE REQUIREMENTS:
- Each attraction MUST include a short descriptive paragraph (2–3 lines).
- Explain why the place is famous or worth visiting.
- Mention historical, cultural, or experiential value.
- Suggest what the traveler should DO there.
- Maintain an engaging, friendly tone.

STRICT COST RULES:
- NEVER invent exact monument entry fees.
- Use ONLY these cost labels:
  • Free
  • Low-cost (₹0–₹100)
  • Moderate (₹100–₹500)
  • Premium (₹500+)
- Food & transport may be estimated as ranges.
- If unsure, say "Cost varies".

FOR EACH DAY INCLUDE:
- Morning / Afternoon / Evening plan
- Attraction name + description + cost label
- Suggested timings
- Local food suggestions with cost range
- Transport estimate
- Estimated daily spend range

Respond in plain text using:
Day 1:
Day 2:
etc.
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional Indian travel guide. "
                    "Be descriptive, engaging, and informative while staying factually safe. "
                    "Never invent exact prices."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.45,
        "max_tokens": 1300
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        itinerary_text = result["choices"][0]["message"]["content"]

        itinerary_text = normalize_costs(itinerary_text)
        itinerary_text = enforce_budget_language(itinerary_text, budget)

        return Response({"itinerary": itinerary_text})

    except Exception as e:
        print("Itinerary generation error:", e)
        return Response(
            {"error": "Failed to generate itinerary"},
            status=500
        )
