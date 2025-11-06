# Deploy to Render.com - Step by Step Guide

This guide will help you deploy your Flask application with WhatsApp integration to Render.com's free tier.

## Prerequisites

1. GitHub account (to connect your repository)
2. Render.com account (free to create)
3. Your environment variables ready (API keys)

---

## Step 1: Push Your Code to GitHub

If you haven't already, push your code to GitHub:

```bash
cd /Users/hendrikdewinne/MOTHERSHIP_PROSPECTING

# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Add WhatsApp integration and prepare for Render deployment"

# Push to GitHub (replace with your repo URL)
git remote add origin https://github.com/yourusername/mothership-prospecting.git
git branch -M main
git push -u origin main
```

---

## Step 2: Create Render Account

1. Go to [https://render.com](https://render.com)
2. Click **"Get Started"** or **"Sign Up"**
3. Sign up with your **GitHub account** (recommended for easy deployment)
4. Authorize Render to access your GitHub repositories

---

## Step 3: Create a New Web Service

1. Once logged in, click **"New +"** in the top right
2. Select **"Web Service"**
3. Choose **"Build and deploy from a Git repository"**
4. Click **"Connect a repository"**
5. Find and select your `mothership-prospecting` repository
6. Click **"Connect"**

---

## Step 4: Configure Your Web Service

Render will auto-detect your Python app. Configure these settings:

### Basic Settings:
- **Name**: `mothership-prospecting` (or any name you prefer)
- **Region**: Choose closest to you (e.g., Oregon USA, Frankfurt EU)
- **Branch**: `main` (or your default branch)
- **Runtime**: `Python 3` (should be auto-detected)

### Build & Deploy Settings:
- **Build Command**: 
  ```
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```
  gunicorn app:app
  ```

### Instance Type:
- Select **"Free"** (or upgrade if you need more resources)

---

## Step 5: Add Environment Variables

Click on **"Environment"** or **"Advanced"** section and add these environment variables:

### Required Variables:

```bash
# OpenAI
OPENAI_API_KEY=sk-your-actual-key-here

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Google (optional)
GOOGLE_MAPS_API_KEY=your-google-maps-key
GEMINI_API_KEY=your-gemini-key

# DUANO (optional)
DUANO_CLIENT_ID=3
DUANO_CLIENT_SECRET=your-duano-secret
DUANO_API_BASE_URL=https://yugen.douano.com
DUANO_REDIRECT_URI=https://your-render-app.onrender.com/oauth/callback
```

**Important**: Update `DUANO_REDIRECT_URI` with your actual Render URL after deployment (see Step 7).

---

## Step 6: Deploy!

1. Click **"Create Web Service"** at the bottom
2. Render will start building and deploying your app
3. This may take 5-10 minutes for the first deployment
4. Watch the logs in real-time to see progress

---

## Step 7: Get Your Live URL

Once deployed, your app will be available at:

```
https://your-app-name.onrender.com
```

For example:
```
https://mothership-prospecting.onrender.com
```

**Copy this URL** - you'll need it for:
1. Twilio webhook configuration
2. DUANO redirect URI (update in Render environment variables)

---

## Step 8: Configure Twilio WhatsApp Webhook

Now that your app is live, configure Twilio:

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to: **Messaging** → **Try it out** → **Send a WhatsApp message**
3. Go to **Sandbox Settings**
4. Set **"When a message comes in"** to:
   ```
   https://your-app-name.onrender.com/api/whatsapp/webhook
   ```
5. Method: **HTTP POST**
6. Save configuration

---

## Step 9: Update DUANO Redirect URI (if using OAuth)

1. Go back to **Render Dashboard**
2. Click on your service
3. Go to **"Environment"**
4. Update `DUANO_REDIRECT_URI` to:
   ```
   https://your-app-name.onrender.com/oauth/callback
   ```
5. Save changes (this will trigger a redeploy)

---

## Step 10: Test Your Deployment

### Test the Website:
```
https://your-app-name.onrender.com
```

### Test WhatsApp:
1. Send a text message to your Twilio WhatsApp number
2. Send a voice note
3. Check the inbox at:
   ```
   https://your-app-name.onrender.com/whatsapp-inbox
   ```

### Check Logs:
- In Render Dashboard → Click your service → **"Logs"** tab
- You should see incoming webhook requests and processing logs

---

## Troubleshooting

### Build Fails
- Check the build logs in Render
- Verify `requirements.txt` has all dependencies
- Make sure Python version is compatible

### App Crashes on Start
- Check the logs for error messages
- Verify all required environment variables are set
- Test locally first: `gunicorn app:app`

### WhatsApp Messages Not Processing
1. Check Render logs for webhook calls
2. Verify Twilio webhook URL is correct
3. Test webhook endpoint:
   ```bash
   curl -X POST https://your-app-name.onrender.com/api/whatsapp/webhook
   ```

### App Goes to Sleep (Free Tier)
- Render free tier apps sleep after 15 minutes of inactivity
- First request after sleep takes ~30 seconds to wake up
- Consider upgrading to paid tier ($7/month) for always-on service

---

## Important Notes for Free Tier

### Limitations:
- ✅ **750 hours/month** (enough for one always-on service)
- ✅ **512 MB RAM** (sufficient for this app)
- ⚠️ **Sleeps after 15 min inactivity** (wakes on first request)
- ⚠️ **Build time limited** to 5 minutes
- ❌ **No custom domain** on free tier (upgrade to add)

### Tips:
1. **Keep app awake**: Use a service like [UptimeRobot](https://uptimerobot.com) to ping your app every 5 minutes
2. **Monitor usage**: Check Render dashboard for usage stats
3. **Upgrade if needed**: $7/month removes sleep restriction

---

## Updating Your App

After making code changes:

```bash
# Commit changes
git add .
git commit -m "Your commit message"

# Push to GitHub
git push origin main
```

Render will **automatically detect the push** and redeploy! 🎉

---

## Custom Domain (Optional - Paid Tier)

To use your own domain (requires paid plan):

1. Upgrade to paid tier ($7/month)
2. Go to **Settings** → **Custom Domains**
3. Add your domain (e.g., `app.yourdomain.com`)
4. Update DNS records as shown by Render
5. SSL certificate is automatically provisioned

---

## Environment Variables Management

### To Update Variables:
1. Go to Render Dashboard
2. Click your service
3. Go to **"Environment"**
4. Edit or add variables
5. **Save** (triggers automatic redeploy)

### Security Best Practices:
- ✅ Never commit `.env` file to GitHub
- ✅ Use Render's encrypted environment variables
- ✅ Rotate API keys regularly
- ✅ Use different keys for staging/production

---

## Monitoring & Logs

### View Logs:
- **Live Logs**: Render Dashboard → Your Service → Logs tab
- **Filters**: Filter by severity (info, warning, error)
- **Download**: Export logs for analysis

### Performance Monitoring:
- **Metrics**: CPU, Memory, Request Count
- **Alerts**: Set up email alerts for downtime
- **Status Page**: Share status with your team

---

## Cost Estimate

### Free Tier:
- **Cost**: $0/month
- **Perfect for**: Development, testing, low-traffic apps

### Paid Tier:
- **Starter**: $7/month (recommended for production)
  - No sleep
  - Always-on
  - Better performance
  - Custom domains

### Additional Services:
- **PostgreSQL**: Free tier available (256MB)
- **Redis**: $10/month
- **Cron Jobs**: Free

---

## Next Steps

1. ✅ Deploy to Render
2. ✅ Configure Twilio webhook
3. ✅ Test WhatsApp integration
4. 📊 Monitor logs and performance
5. 🚀 Share your live URL!

---

## Support Resources

- **Render Docs**: [https://render.com/docs](https://render.com/docs)
- **Render Community**: [https://community.render.com](https://community.render.com)
- **Twilio Support**: [https://support.twilio.com](https://support.twilio.com)

---

## Your URLs After Deployment

After completing these steps, you'll have:

```
🌐 Website:    https://your-app-name.onrender.com
📱 WhatsApp:   https://your-app-name.onrender.com/whatsapp-inbox
🔗 Webhook:    https://your-app-name.onrender.com/api/whatsapp/webhook
📊 Dashboard:  https://your-app-name.onrender.com/
```

**Congratulations! Your app is now live! 🎉**

