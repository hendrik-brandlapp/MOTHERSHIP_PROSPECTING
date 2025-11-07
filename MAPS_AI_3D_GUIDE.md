# Maps AI 3D - Photorealistic 3D Maps with Agentic Intelligence

## 🌍 The Ultimate Maps Experience

**Maps AI 3D** brings the [Google AI Studio "Chat with Maps Live"](https://ai.studio/apps/bundled/chat_with_maps_live) experience to your DOUANO app, featuring photorealistic 3D maps and intelligent agentic behavior.

Inspired by the [Yugen Kombucha demo](http://github.com/hendrik-netizen/Yugen-Kombucha), this implementation includes:

- 🗺️ **Photorealistic 3D Maps** - Like Google Earth in your browser
- 🤖 **Agentic Tool Functions** - Smart camera control and location framing
- 🎥 **Cinematic Camera Animations** - Smooth fly-to transitions
- 📍 **Rich Location Cards** - Photos, ratings, and details
- 🎨 **Immersive Dark UI** - Designed for 3D visualization

## 🚀 Access It Now

Visit: **`http://localhost:5002/maps-ai-3d`**

Or click **"Maps AI 3D"** in the navigation menu (cube icon)

## ✨ Key Features

### 1. **Photorealistic 3D Maps**

Unlike standard 2D maps, this uses Google's **`<gmp-map-3d>`** web component for photorealistic 3D rendering:

- Real satellite imagery in 3D
- Accurate building heights and structures
- Natural terrain representation
- Cinematic viewing angles

### 2. **Agentic Tool Functions**

The AI automatically uses intelligent tools:

#### `frameEstablishingShot`
Flies the camera to a specific location with cinematic parameters:
- Custom range (zoom level)
- Tilt angle for best view
- Heading direction
- Smooth 3-second animation

**Example**: "Show me the Eiffel Tower"
→ Camera flies to Paris, frames the tower perfectly

#### `frameLocations`
Shows multiple places simultaneously:
- Calculates optimal bounding box
- Frames all locations in view
- Adjusts range automatically
- Perfect for comparing places

**Example**: "Find the top 3 restaurants in Tokyo"
→ Camera frames all 3 locations at once

#### `mapsGrounding`
Uses Google Maps data for accuracy:
- Real-time place information
- Ratings and reviews
- Opening hours
- Exact coordinates

### 3. **Smart Camera Control**

**Automatic Behavior**:
- "Show me..." → Flies to location
- "Find..." → Shows all results on map
- "Take me to..." → Cinematic transition
- "Explore..." → Optimal viewing angle

**Manual Controls**:
- 🏠 **Reset**: Return to your location
- ✖️ **Clear**: Remove all location markers

### 4. **Rich Location Information**

Beautiful overlay cards display:
- 📸 Place name and icon
- ⭐ Star ratings and review counts
- 📍 Full address
- 🕐 Open/Closed status
- Auto-disappear after 10 seconds

### 5. **Immersive Dark Interface**

- **Split-screen layout**: Chat left, 3D map right
- **Dark theme**: Optimized for map visualization
- **Gradient accents**: Purple/blue theme
- **Smooth animations**: Professional feel

## 🎯 How to Use

### Example Queries

#### Explore Famous Landmarks
```
"Show me the Eiffel Tower in Paris"
"Take me to the Statue of Liberty"
"Fly to Machu Picchu"
```
→ Camera flies with cinematic animation to the location

#### Find Places
```
"Find kombucha bars in Ghent"
"What are the best Italian restaurants in New York?"
"Show me cafes with outdoor seating near me"
```
→ Displays multiple locations with overlay cards

#### Compare Locations
```
"Compare the top hotels in Tokyo"
"Show me the 3 best pizza places in Chicago"
```
→ Frames all locations simultaneously on the map

#### Plan Trips
```
"Plan a day in San Francisco"
"What should I see in Rome?"
```
→ Shows multiple tourist spots on the 3D map

## 🎥 Camera Animation System

The camera system uses smooth easing for cinematic feel:

```javascript
// Cubic easing for smooth acceleration/deceleration
const eased = 1 - Math.pow(1 - progress, 3);

// Interpolate all camera parameters
- center (lat/lng)
- range (zoom)
- tilt (viewing angle)
- heading (direction)
```

**Default Parameters**:
- Range: 400-1000m (depending on context)
- Tilt: 60-70° (for optimal 3D view)
- Heading: 0° (north) or custom
- Duration: 3 seconds

## 🔧 Architecture

### Frontend Components

**3D Map Element**:
```html
<gmp-map-3d 
    center="51.0543,3.7174"
    range="1000"
    tilt="60"
    heading="0"
></gmp-map-3d>
```

**Camera Control**:
- `flyToLocation()` - Animate to single location
- `frameLocations()` - Frame multiple locations
- `resetCamera()` - Return to user location
- `clearLocations()` - Clear UI overlays

**UI Components**:
- Chat sidebar with dark theme
- Location overlay cards
- Map control buttons
- Loading overlay
- Typing indicators

### Backend Architecture

**Tool Processing Pipeline**:

```
User Query
    ↓
Gemini 2.0 + Maps Grounding
    ↓
Extract Place IDs
    ↓
Google Places API Details
    ↓
Determine Tool Function
    ↓
Return Tool Results + Response
    ↓
Frontend Executes Camera Control
```

**System Instruction**:
The AI is configured with agentic behavior:
- Automatically use tools when appropriate
- Provide rich location details
- Be conversational and proactive
- Cite Google Maps sources

## 🆚 Comparison: Three Maps AI Experiences

| Feature | Maps AI | Maps AI Enhanced | **Maps AI 3D** |
|---------|---------|------------------|----------------|
| **Interface** | Text chat | Split-screen 2D | Split-screen 3D |
| **Map Type** | None | Google Maps 2D | Photorealistic 3D |
| **View** | Links only | Flat map | 3D buildings & terrain |
| **Camera Control** | ❌ | Basic | ✅ **Cinematic** |
| **Agentic Tools** | ❌ | Limited | ✅ **Full** |
| **Location Cards** | ❌ | Bottom panel | ✅ **Floating overlay** |
| **Animations** | ❌ | Basic | ✅ **Smooth fly-to** |
| **Immersion** | Low | Medium | ✅ **High** |
| **Best For** | Quick questions | Comparing places | **Exploration & visualization** |

## 💡 Pro Tips

### Get Cinematic Views

1. **Use "Show me..."** for automatic framing
   - "Show me the Golden Gate Bridge" → Perfect angle
   
2. **Request specific views**
   - "Take me high above Tokyo" → High altitude view
   - "Give me a close-up of the Colosseum" → Closer range

3. **Compare multiple places**
   - "Show me the top 3 museums in London" → All in frame

### Explore Effectively

1. **Start broad, then zoom in**
   - "Show me Paris" → Overview
   - "Find the Louvre" → Specific location

2. **Use location context**
   - "What's near me?" → Uses your location
   - "Find restaurants within 1km" → Local search

3. **Combine queries**
   - "Show me Central Park and then Times Square"
   - AI handles sequential commands

## 🔥 Advanced Features

### System Instruction

The AI has a custom system prompt for agentic behavior:

```
You are an intelligent location-aware AI assistant 
with access to photorealistic 3D maps.

Your capabilities:
1. frameEstablishingShot: Fly the camera to locations
2. mapsGrounding: Search Google Maps
3. frameLocations: Show multiple places

When users ask about places:
- Automatically use mapsGrounding
- Fly the camera to show the location
- Provide rich details

Be conversational, helpful, and proactive.
```

### Camera Parameter Optimization

The system automatically calculates optimal views:

**Single Location**:
- Range: 500m (close view)
- Tilt: 65° (good 3D perspective)

**Multiple Locations**:
- Range: Calculated from bounding box + 50% padding
- Tilt: 60° (wider perspective)
- Center: Geographic midpoint

### Loading States

- 🔄 **Loading Overlay**: Shows during API calls
- 💬 **Typing Indicator**: While AI thinks
- 🎬 **Camera Animation**: Smooth 3-second transitions

## 🐛 Troubleshooting

### 3D Map Not Loading

**Problem**: Black screen or gray box  
**Solutions**:
1. Check that `GOOGLE_MAPS_API_KEY` is set
2. Ensure the key has "Maps JavaScript API" enabled
3. Try refreshing the page
4. Check browser console for errors

### Camera Not Moving

**Problem**: Map doesn't fly to locations  
**Solutions**:
1. Wait for map to fully load (check console)
2. Try a more specific query
3. Manually click reset button

### Location Cards Not Appearing

**Problem**: No overlay cards show up  
**Solutions**:
1. Query must return place results
2. Try being more specific: "restaurants in Paris" not just "Paris"
3. Check if places have required data (coordinates, names)

### Slow Performance

**Problem**: Choppy animations or slow loading  
**Solutions**:
1. Close other browser tabs
2. Use Chrome/Edge for best WebGL performance
3. Reduce window size if needed
4. Check internet connection

## 🎓 Learning from the Best

### Yugen Kombucha Implementation

The [Yugen Kombucha repo](http://github.com/hendrik-netizen/Yugen-Kombucha) uses:

**React Architecture**:
- Custom `Map3D` component wrapper
- `useLiveApi` hook for Gemini
- Tool registry pattern
- `@vis.gl/react-google-maps`

**Our Flask Implementation**:
- Vanilla JavaScript (no React needed)
- Direct `<gmp-map-3d>` usage
- Server-side tool processing
- Simplified but powerful

**Shared Concepts**:
- 3D photorealistic maps
- Agentic tool functions
- Camera control utilities
- Maps grounding integration

### Key Differences

| Aspect | Yugen Kombucha | Our Implementation |
|--------|----------------|-------------------|
| Framework | React/TypeScript | Flask/Vanilla JS |
| Audio | Gemini Live API | Text-only |
| Tools | Client-side | Server-side |
| Complexity | Higher | Simpler |
| Customization | More code | More accessible |

## 🚀 Future Enhancements

### Planned Features

1. **Voice Control**
   - Add Gemini Live API
   - Voice commands for navigation
   - Real-time conversation

2. **Multi-day Planning**
   - Save locations
   - Build itineraries
   - Share trip plans

3. **Custom Markers**
   - 3D marker models
   - Animated pins
   - Colored categories

4. **Enhanced Tools**
   - `showRoute` - Display directions
   - `compareLocations` - Side-by-side view
   - `tourMode` - Automated tour

5. **Offline Support**
   - Cache visited locations
   - Offline map tiles
   - Saved favorites

## 📊 Performance Metrics

**Loading Times**:
- Initial map load: ~2-3 seconds
- Camera animation: 3 seconds
- API response: 1-2 seconds
- Place details: 0.5-1 second

**Optimization**:
- Lazy load 3D tiles
- Limit to 5 places per query
- Cache place details
- Smooth 60fps animations

## 🎉 Summary

**Maps AI 3D** brings the power of Google's photorealistic 3D maps with intelligent AI control to your fingertips. It's:

- 🎬 **Cinematic**: Smooth camera animations
- 🤖 **Smart**: Agentic tool usage
- 🌍 **Immersive**: 3D photorealistic views
- ⚡ **Fast**: Optimized performance
- 🎨 **Beautiful**: Professional dark UI

**Perfect for**:
- 🗺️ Exploring new cities
- 🏨 Planning trips
- 🍽️ Finding restaurants
- 🌆 Visualizing locations
- 📍 Comparing places

**Start your journey**: `http://localhost:5002/maps-ai-3d`

---

**Inspired by**:
- [Google AI Studio - Chat with Maps Live](https://ai.studio/apps/bundled/chat_with_maps_live)
- [Yugen Kombucha Demo](http://github.com/hendrik-netizen/Yugen-Kombucha)

**Powered by**:
- Google Gemini 2.0 Flash
- Google Maps 3D API
- Google Places API
- Flask + Python

🚀 **Experience the future of location-based AI!**

