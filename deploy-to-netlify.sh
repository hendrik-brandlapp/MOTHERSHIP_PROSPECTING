#!/bin/bash

# Netlify Deployment Script for DOUANO
echo "🚀 Preparing DOUANO for Netlify deployment..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit for Netlify deployment"
fi

# Check if Netlify CLI is installed
if ! command -v netlify &> /dev/null; then
    echo "📦 Installing Netlify CLI..."
    npm install -g netlify-cli
fi

# Check if user is logged in to Netlify
if ! netlify status &> /dev/null; then
    echo "🔐 Please log in to Netlify..."
    netlify login
fi

# Initialize Netlify site (if not already done)
if [ ! -f ".netlify/state.json" ]; then
    echo "🏗️  Initializing Netlify site..."
    netlify init
fi

# Deploy to production
echo "🚀 Deploying to Netlify..."
netlify deploy --prod

echo "✅ Deployment complete!"
echo "🌐 Your site should now be live at the URL shown above"
echo ""
echo "📝 Next steps:"
echo "1. Update your OAuth redirect URIs to use your new Netlify domain"
echo "2. Set up any required environment variables in Netlify dashboard"
echo "3. Test the OAuth flow and API endpoints"
echo ""
echo "📚 For more information, see NETLIFY_DEPLOYMENT.md"
