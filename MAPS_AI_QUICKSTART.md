# Maps AI Quick Start Guide

Get started with Maps AI in 3 simple steps!

## Step 1: Get Your Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click "Create API Key" 
4. Copy your new API key

## Step 2: Configure Your Environment

Add your API key to your `.env` file:

```bash
# Open or create .env file
echo "GEMINI_API_KEY=your_api_key_here" >> .env
```

Or manually edit `.env` and add:
```
GEMINI_API_KEY=AIza...your_key_here
```

## Step 3: Run the Application

```bash
# Activate virtual environment
source venv/bin/activate   # On Mac/Linux
# or
.\venv\Scripts\activate    # On Windows

# Run the app
python app.py
```

## Access Maps AI

1. Open your browser to `http://localhost:5001`
2. Login with your DOUANO credentials
3. Click "Maps AI" in the navigation menu
4. Start chatting!

## Try These Example Queries

**Find Restaurants:**
```
What are the best Italian restaurants within a 15-minute walk from here?
```

**Plan a Day:**
```
Plan a day in San Francisco for me. I want to see the Golden Gate Bridge, visit a museum, and have a nice dinner.
```

**Local Questions:**
```
Find coffee shops with outdoor seating near me
```

**Get Recommendations:**
```
Which family-friendly restaurants near here have the best reviews?
```

## Tips

- ✅ Allow location access in your browser for better results
- ✅ Be specific about what you're looking for
- ✅ Include preferences (distance, price, amenities)
- ✅ Ask follow-up questions to refine results

## Need Help?

See the full [Maps AI Guide](MAPS_AI_GUIDE.md) for detailed documentation.

---

**That's it! You're ready to explore with Maps AI! 🗺️✨**

