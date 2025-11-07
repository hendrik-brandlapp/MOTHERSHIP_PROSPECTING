# Maps AI - Google Gemini with Maps Grounding

## Overview

Maps AI is a new feature that integrates Google's Gemini 2.0 with Google Maps grounding to provide intelligent, location-aware responses. This powerful combination allows users to ask natural language questions about places, get travel recommendations, plan itineraries, and more.

## Features

✨ **Natural Language Queries**: Ask questions about locations in plain English
🗺️ **Google Maps Integration**: Responses grounded in real-time Google Maps data  
📍 **Location Awareness**: Automatically uses your current location for better results
🔗 **Source Citations**: Every response includes links to Google Maps sources
💬 **Chat Interface**: Beautiful, modern chat UI with typing indicators
⚡ **Real-time Responses**: Fast responses powered by Gemini 2.0 Flash

## Setup Instructions

### 1. Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key

### 2. Configure Environment Variables

Add your Gemini API key to your `.env` file:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

You can also copy from `ENV.EXAMPLE`:

```bash
cp ENV.EXAMPLE .env
# Then edit .env and add your GEMINI_API_KEY
```

### 3. Install Dependencies

The required package is already in `requirements.txt`. If you haven't installed it yet:

```bash
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

Visit `http://localhost:5001/maps-ai` (or your configured port)

## How to Use

### Basic Queries

Ask natural questions about places:

- "What are the best Italian restaurants within a 15-minute walk from here?"
- "Find coffee shops with outdoor seating near me"
- "What's the top-rated pizza place in Manhattan?"

### Travel Planning

Plan complete itineraries:

- "Plan a day in San Francisco for me. I want to see the Golden Gate Bridge, visit a museum, and have a nice dinner"
- "Create a weekend itinerary for Paris with museums, cafes, and shopping"
- "What should I do in Tokyo for 3 days?"

### Location-Specific Questions

Get details about specific places:

- "Is there a cafe on the corner of 1st and Main that has outdoor seating?"
- "What are the hours for the Metropolitan Museum?"
- "Does this restaurant have good vegetarian options?"

### Recommendations

Get personalized recommendations:

- "Which family-friendly restaurants near here have the best playground reviews?"
- "Find me boutique hotels in downtown Seattle with rooftop bars"
- "What are the best hiking trails within 30 minutes of downtown?"

## Example Interactions

### Example 1: Restaurant Search

**User**: "What are the best Italian restaurants within a 15-minute walk from here?"

**Maps AI**: Based on your location, here are some excellent Italian restaurants within walking distance:

1. **Trattoria Roma** - Authentic Italian cuisine with handmade pasta
2. **Bella Vista Ristorante** - Known for wood-fired pizzas and fresh seafood
3. **Il Padrino** - Family-owned restaurant with traditional recipes

*[Includes Google Maps links to each location]*

### Example 2: Day Planning

**User**: "Plan a day in San Francisco for me with the Golden Gate Bridge, a museum, and dinner"

**Maps AI**: Here's a perfect day in San Francisco:

**Morning (9:00 AM)**: Start at the Golden Gate Bridge. Walk across for stunning views.

**Lunch (12:30 PM)**: Grab lunch at Fort Point, with views of the bridge.

**Afternoon (2:00 PM)**: Visit the de Young Museum in Golden Gate Park.

**Evening (6:30 PM)**: Dinner at Nopa, a popular spot with excellent California cuisine.

*[Includes timing, distances, and Google Maps links]*

## Technical Details

### Architecture

- **Frontend**: HTML/CSS/JavaScript with modern chat UI
- **Backend**: Flask Python server
- **AI Model**: Gemini 2.0 Flash Experimental
- **Grounding**: Google Maps API integration
- **Location**: Browser geolocation API

### API Endpoints

#### GET `/maps-ai`
Returns the Maps AI chat interface

#### POST `/api/maps-ai/chat`
Processes chat messages with Maps grounding

**Request Body**:
```json
{
  "message": "Find Italian restaurants near me",
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  "history": []
}
```

**Response**:
```json
{
  "success": true,
  "response": "Here are some great Italian restaurants...",
  "sources": [
    {
      "title": "Trattoria Roma",
      "uri": "https://maps.google.com/?cid=...",
      "place_id": "ChIJ..."
    }
  ]
}
```

### How Maps Grounding Works

1. **User Query**: You ask a question about locations
2. **Location Context**: Your browser location is sent (if permitted)
3. **Gemini Processing**: Gemini analyzes the query and determines if Maps data would help
4. **Maps Grounding**: Gemini queries Google Maps for relevant place information
5. **Response Generation**: Gemini generates a response using Maps data
6. **Source Attribution**: Response includes citations to Google Maps sources

### Privacy

- Location data is only used for the current query
- Location sharing requires browser permission
- No location data is stored on the server
- All queries are processed through Google's secure APIs

## Troubleshooting

### "Gemini API is not configured" Error

**Solution**: Make sure you've added `GEMINI_API_KEY` to your `.env` file and restarted the application.

### Location not detected

**Solution**: 
1. Check browser permissions for location access
2. You can still use Maps AI without location - just be more specific in your queries
3. Try using "in [city name]" in your query

### No sources returned

**Solution**: 
- Some queries may not trigger Maps grounding
- Try being more specific about location in your query
- Make sure your query is location-related

### Rate Limits

Google Gemini API has rate limits:
- Free tier: 15 requests per minute
- Paid tier: Higher limits available

If you hit rate limits, wait a minute before trying again.

## Cost Information

### Gemini API Pricing

- **Grounding with Google Maps**: $25 per 1,000 grounded prompts
- **Gemini 2.0 Flash**: Included in grounding price
- **Free Tier**: Limited free usage available

Visit [Google AI Pricing](https://ai.google.dev/pricing) for current rates.

## Best Practices

### Writing Good Queries

✅ **Good**:
- "What are the best Italian restaurants within a 15-minute walk from here?"
- "Plan a day in San Francisco with the Golden Gate Bridge, museum, and dinner"
- "Find family-friendly restaurants near me with playgrounds"

❌ **Less Effective**:
- "Food" (too vague)
- "Tell me about restaurants" (no location context)
- "What should I do?" (no location or context)

### Tips for Best Results

1. **Be Specific**: Include location details, preferences, or constraints
2. **Use Location**: Allow browser location for more relevant results
3. **Ask Follow-ups**: Build on previous queries for better context
4. **Include Criteria**: Mention distance, price range, amenities, etc.

## Advanced Features

### Future Enhancements

Planned features for future versions:

- 🗺️ **Interactive Map View**: Visualize results on an embedded map
- 💾 **Save Favorites**: Save places and itineraries
- 📱 **Share Itineraries**: Export and share travel plans
- 🔄 **Multi-day Planning**: Plan entire trips with accommodation
- 🌐 **Multi-language**: Support for queries in multiple languages
- 🎨 **Customization**: Personalize recommendations based on preferences

### API Integration

You can integrate Maps AI into your own applications:

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")

response = client.models.generate_content(
    model='gemini-2.0-flash-exp',
    contents="Find Italian restaurants near Times Square",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_maps=types.GoogleMaps())],
        tool_config=types.ToolConfig(
            retrieval_config=types.RetrievalConfig(
                lat_lng=types.LatLng(
                    latitude=40.758896,
                    longitude=-73.985130
                )
            )
        )
    )
)

print(response.text)
```

## Resources

### Documentation

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Grounding with Google Maps](https://ai.google.dev/gemini-api/docs/grounding)
- [Google Maps Platform](https://developers.google.com/maps)

### Tutorials

- [Gemini API Quickstart](https://ai.google.dev/tutorials/get_started_web)
- [Maps Grounding Cookbook](https://colab.research.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Grounding.ipynb)

### Support

- [Google AI Studio](https://aistudio.google.com/)
- [GitHub Issues](https://github.com/google/generative-ai-python/issues)

## Changelog

### Version 1.0.0 (2024-10-19)

- ✨ Initial release of Maps AI
- 🗺️ Google Maps grounding integration
- 💬 Modern chat interface
- 📍 Location awareness
- 🔗 Source citations
- ⚡ Real-time responses

## License

This feature uses:
- Google Gemini API (subject to Google's terms)
- Google Maps data (subject to Google Maps terms)
- Flask (BSD License)

---

**Built with ❤️ using Google Gemini and Google Maps**

For questions or issues, please refer to the main project documentation.

