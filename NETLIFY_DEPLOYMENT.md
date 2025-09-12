# Netlify Deployment Guide

This guide will help you deploy your DOUANO application to Netlify.

## Prerequisites

1. A Netlify account (free at netlify.com)
2. Git repository with your code
3. Node.js installed locally (for testing)

## Deployment Steps

### Option 1: Deploy via Netlify UI (Recommended)

1. **Push your code to GitHub/GitLab/Bitbucket**
   ```bash
   git add .
   git commit -m "Prepare for Netlify deployment"
   git push origin main
   ```

2. **Connect to Netlify**
   - Go to [netlify.com](https://netlify.com) and sign in
   - Click "New site from Git"
   - Choose your Git provider and repository
   - Select the branch you want to deploy (usually `main`)

3. **Configure build settings**
   - Build command: `npm run build`
   - Publish directory: `public`
   - Functions directory: `netlify/functions`

4. **Set environment variables** (if needed)
   - Go to Site settings > Environment variables
   - Add any required environment variables

5. **Deploy**
   - Click "Deploy site"
   - Netlify will automatically build and deploy your site

### Option 2: Deploy via Netlify CLI

1. **Install Netlify CLI**
   ```bash
   npm install -g netlify-cli
   ```

2. **Login to Netlify**
   ```bash
   netlify login
   ```

3. **Initialize and deploy**
   ```bash
   netlify init
   netlify deploy --prod
   ```

## Project Structure

```
├── public/                 # Static files (HTML, CSS, JS)
│   ├── index.html         # Main page
│   ├── css/               # Stylesheets
│   └── js/                # JavaScript files
├── netlify/
│   └── functions/         # Serverless functions
│       ├── api.js         # Main API handler
│       └── package.json   # Function dependencies
├── netlify.toml           # Netlify configuration
└── package.json           # Build configuration
```

## Important Notes

### Limitations
- **Server-side rendering**: Your Flask templates have been converted to static HTML
- **Session management**: OAuth tokens will need to be handled client-side
- **Database connections**: Direct database connections won't work in serverless functions

### Required Changes
1. **OAuth flow**: Update redirect URIs to use your Netlify domain
2. **API endpoints**: Implement proper error handling in Netlify functions
3. **Environment variables**: Set up any required API keys in Netlify

### Custom Domain
- After deployment, you can add a custom domain in Netlify settings
- Update your OAuth redirect URIs accordingly

## Troubleshooting

### Build Errors
- Check that all dependencies are properly listed in `package.json`
- Ensure the build command is correct
- Verify the publish directory exists

### Function Errors
- Check Netlify function logs in the dashboard
- Ensure all required environment variables are set
- Verify CORS headers are properly configured

### OAuth Issues
- Update redirect URIs to match your Netlify domain
- Check that client credentials are correct
- Verify the OAuth flow is working in the browser

## Support

For issues specific to Netlify deployment:
- [Netlify Documentation](https://docs.netlify.com/)
- [Netlify Functions Guide](https://docs.netlify.com/functions/overview/)
- [Netlify Community](https://community.netlify.com/)
