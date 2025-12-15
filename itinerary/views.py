from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# -------------------------------------------------
# INDIA-SPECIFIC CONFIG
# -------------------------------------------------

INDIA_INTEREST_MAP = {
    "Temples & Shrines": "temples, shrines, religious sites",
    "Forts & Palaces": "historic forts, palaces, royal heritage",
    "Cultural Heritage": "cultural heritage, traditional arts",
    "Traditional Food": "local cuisine, street food, traditional dishes",
    "Museums & Art Galleries": "museums, art galleries, exhibitions"
}

# Known places that always have free entry
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

# Daily budget caps
BUDGET_CAPS = {
    "Budget Friendly": 2000,
    "Moderate": 5000,
    "Luxury Experience": 15000
}


# -------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------

def normalize_costs(text):
    """Force known free places to always show as Free"""
    for place in KNOWN_FREE_PLACES:
        text = text.replace(f"{place} – Low-cost", f"{place} – Free")
        text = text.replace(f"{place} – Moderate", f"{place} – Free")
        text = text.replace(f"{place} – Premium", f"{place} – Free")
    return text


def extract_range(text, label):
    """
    Extracts ₹min–₹max from lines like:
    'Food per day: ₹300–₹400'
    """
    match = re.search(
        rf"{label}.*?₹\s*(\d+)\s*[–-]\s*(\d+)",
        text,
        re.IGNORECASE
    )
    if match:
        return int(match.group(1)), int(match.group(2))
    return 0, 0


def get_day_count(trip_duration):
    return {
        "1-day": 1,
        "2–3 days": 3,
        "Week": 7
    }.get(trip_duration, 1)


def build_trip_budget_card(itinerary_text, days, budget):
    attractions = extract_range(itinerary_text, "Attractions per day")
    food = extract_range(itinerary_text, "Food per day")
    transport = extract_range(itinerary_text, "Transport per day")

    total_min = (attractions[0] + food[0] + transport[0]) * days
    total_max = (attractions[1] + food[1] + transport[1]) * days

    cap = BUDGET_CAPS.get(budget)

    warning = ""
    if cap and total_max > cap * days:
        warning = (
            "\n⚠️ Note: This plan is at the higher end of your selected budget. "
            "Consider reducing premium activities or dining choices."
        )

    return f"""
--------------------------------
TOTAL TRIP BUDGET BREAKDOWN
--------------------------------
Trip Duration: {days} Days
Budget Category: {budget}

Attractions: ₹{attractions[0] * days} – ₹{attractions[1] * days}
Food: ₹{food[0] * days} – ₹{food[1] * days}
Local Transport: ₹{transport[0] * days} – ₹{transport[1] * days}

--------------------------------
Estimated Total Trip Cost:
₹{total_min} – ₹{total_max}
--------------------------------
{warning}
"""


# -------------------------------------------------
# API VIEW
# -------------------------------------------------

@api_view(['POST'])
def generate_itinerary(request):
    """
    Generates a budget-aware, India-specific itinerary
    with a combined trip budget card at the end.
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
        f"User current coordinates: {location}. "
        if location else ""
    )

    budget_guidance = {
        "Budget Friendly": "Keep daily expenses under ₹2,000 using free attractions, street food, and public transport.",
        "Moderate": "Daily expenses between ₹2,000–₹5,000 with a balance of comfort and value.",
        "Luxury Experience": "Flexible spending with premium experiences above ₹5,000 per day."
    }.get(budget, "")

    # -------------------------------------------------
    # PROMPT
    # -------------------------------------------------

    prompt = f"""
You are an expert Indian travel planning and budgeting assistant.

{location_str}
Plan a {trip_duration} trip in {city}.

User Budget Category: {budget}
Budget Guidance: {budget_guidance}
User Interests: {interest_str}

STRICT COST RULES (MANDATORY):
- NEVER give exact monument entry fees.
- Use ONLY these cost labels for attractions:
  • Free
  • Low-cost (₹0–₹100)
  • Moderate (₹100–₹500)
  • Premium (₹500+)
- Food costs may be estimated per meal.
- Transport costs may be estimated per day.
- If unsure, say "Cost varies".

For EACH DAY include:
- Attractions with cost label
- Suggested visit timings
- Estimated food cost range
- Estimated local transport cost
- Estimated total daily spend range

At the END, include:

BUDGET_SUMMARY:
- Attractions per day: ₹X–₹Y
- Food per day: ₹X–₹Y
- Transport per day: ₹X–₹Y

Respond ONLY in plain text using:
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
                    "You are an Indian travel budgeting expert. "
                    "Never invent exact entry fees. "
                    "Use ranges and cost categories only."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1200
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

        days = get_day_count(trip_duration)
        budget_card = build_trip_budget_card(
            itinerary_text,
            days,
            budget
        )

        itinerary_text += "\n\n" + budget_card

        return Response({"itinerary": itinerary_text})

    except Exception as e:
        print("Itinerary generation error:", e)
        return Response(
            {"error": "Failed to generate itinerary"},
            status=500
        )
