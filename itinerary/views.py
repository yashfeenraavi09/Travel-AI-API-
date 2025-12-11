from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Note: Groq now uses OpenAI-compatible chat completions endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

@api_view(['POST'])
def generate_itinerary(request):
    data = request.data
    tripDuration = data.get('tripDuration')
    budget = data.get('budget')
    interests = data.get('interests', [])
    mobility = data.get('mobility')

    prompt = f"""
    Create a detailed travel itinerary:
    Duration: {tripDuration}
    Budget: {budget}
    Interests: {', '.join(interests)}
    Mobility: {mobility}
    Provide day-wise schedule with attractions, activities, and timings.
    """

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.1-8b-instant",  # or another model Groq provides
        "messages": [
            {"role": "system", "content": "You are a helpful travel assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 600
    }

    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        # Groq chat completion returns content here
        itinerary_text = result["choices"][0]["message"]["content"]

        return Response({"itinerary": itinerary_text})
    except Exception as e:
        print("Error generating itinerary:", e)
        return Response({"error": "Failed to generate itinerary"}, status=500)
