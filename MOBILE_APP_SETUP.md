# Mobile App Setup - Install FutBot Pro on Your Phone

FutBot Pro is now a **Progressive Web App (PWA)** that can be installed on your mobile device and works like a native app!

## Quick Start

### Step 1: Access Your Railway Deployment

1. Get your Railway deployment URL (e.g., `https://futbot-production.up.railway.app`)
2. Open this URL in your mobile browser (Safari on iOS, Chrome on Android)

### Step 2: Install on iOS (iPhone/iPad)

1. Open the dashboard in **Safari** (not Chrome - PWAs only work in Safari on iOS)
2. Tap the **Share** button (square with arrow pointing up)
3. Scroll down and tap **"Add to Home Screen"**
4. Customize the name if desired (default: "FutBot Pro")
5. Tap **"Add"** in the top right
6. The app icon will appear on your home screen!

### Step 3: Install on Android

1. Open the dashboard in **Chrome** browser
2. You'll see an **"Install"** banner at the bottom, OR
3. Tap the **menu** (three dots) → **"Install app"** or **"Add to Home screen"**
4. Tap **"Install"** in the popup
5. The app will be installed and appear in your app drawer!

## Features

Once installed, FutBot Pro will:

✅ **Work offline** - Basic functionality cached for offline use  
✅ **Full screen** - No browser UI, looks like a native app  
✅ **Fast loading** - Service worker caches resources  
✅ **Mobile optimized** - Responsive design for phones and tablets  
✅ **Home screen icon** - Easy access from your phone  

## Accessing Your App

### After Installation

- **iOS**: Tap the FutBot Pro icon on your home screen
- **Android**: Find "FutBot Pro" in your app drawer or home screen

### Opening in Browser

You can still access it via browser:
- Just open your Railway URL in any browser
- The PWA features work automatically

## Troubleshooting

### iOS Issues

**"Add to Home Screen" not showing:**
- Make sure you're using **Safari** (not Chrome or other browsers)
- Try refreshing the page
- Make sure the site is fully loaded

**App not working offline:**
- PWAs on iOS have limited offline support
- You need an internet connection for live trading features
- Basic UI is cached for offline viewing

### Android Issues

**Install prompt not showing:**
- Make sure you're using **Chrome** browser
- The site must be served over HTTPS (Railway provides this automatically)
- Try clearing browser cache and reloading

**App crashes:**
- Check Railway logs for server errors
- Make sure your API keys are configured in Railway environment variables

## Updating the App

When you update the code and push to Railway:

1. **Automatic**: The service worker will update automatically
2. **Manual**: 
   - iOS: Delete and re-add to home screen
   - Android: The app will prompt you to update

## Local Development

To test PWA features locally:

```bash
# Start the server
python main.py --mode api --port 8000

# Access on your phone:
# 1. Find your computer's local IP: ifconfig (Mac/Linux) or ipconfig (Windows)
# 2. On your phone, go to: http://YOUR_LOCAL_IP:8000
# 3. Follow installation steps above
```

**Note**: For PWA features to work locally, you may need to use HTTPS. Railway provides HTTPS automatically.

## Security Notes

- The app uses HTTPS (provided by Railway)
- API keys are stored securely in Railway environment variables
- Never commit API keys to your code
- The service worker only caches static resources, not sensitive data

## Features Available on Mobile

✅ View dashboard and analytics  
✅ Start/stop trading  
✅ Monitor positions and P&L  
✅ View trade history  
✅ Check regime analysis  
✅ View performance metrics  

## Limitations

- **Offline trading**: Not supported (requires live connection)
- **Complex charts**: May be slower on older devices
- **Notifications**: Browser notifications work, but may be limited on mobile

## Need Help?

If you encounter issues:

1. Check Railway deployment logs
2. Verify environment variables are set
3. Test in a regular browser first
4. Check browser console for errors (on mobile, use remote debugging)

Enjoy trading on the go! 📱📈


