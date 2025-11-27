# Deploying FutBot Pro to Railway

This guide explains how to deploy your FutBot Pro trading system to [Railway.app](https://railway.app).

## Prerequisites

1.  A GitHub account.
2.  A Railway account (login with GitHub).
3.  Your Alpaca API keys (Paper or Live).

## Step 1: Push Code to GitHub

1.  **Create a New Repository** on GitHub:
    *   Go to [github.com/new](https://github.com/new).
    *   Name it `FutBot-Pro` (or similar).
    *   Make it **Private** (important to protect your strategy).
    *   Do **not** initialize with README, .gitignore, or License (we already have them).
    *   Click "Create repository".

2.  **Push Local Code**:
    Run the following commands in your terminal (replace `YOUR_USERNAME` with your actual GitHub username):

    ```bash
    # Link your local folder to the new GitHub repo
    git remote add origin https://github.com/YOUR_USERNAME/FutBot-Pro.git

    # Rename branch to main (if not already)
    git branch -M main

    # Push the code
    git push -u origin main
    ```

## Step 2: Deploy on Railway

1.  **New Project**:
    *   Go to [Railway Dashboard](https://railway.app/dashboard).
    *   Click "New Project" -> "Deploy from GitHub repo".
    *   Select the `FutBot-Pro` repo you just created.
    *   Click "Deploy Now".

2.  **Environment Variables**:
    *   Once the project is created, go to the **Variables** tab.
    *   Add the following variables (copy from your local `.env` or `.env.local`):
        *   `ALPACA_API_KEY`: Your Alpaca API Key ID.
        *   `ALPACA_SECRET_KEY`: Your Alpaca Secret Key.
        *   `ALPACA_BASE_URL`: `https://paper-api.alpaca.markets` (for paper) or `https://api.alpaca.markets` (for live).
        *   `PORT`: `8000` (Railway usually sets this automatically, but good to set).

3.  **Verify Deployment**:
    *   Go to the **Settings** tab.
    *   Under "Networking", generate a domain (e.g., `futbot-production.up.railway.app`).
    *   Visit that URL in your browser. You should see the FutBot Dashboard!

## Step 3: Offline Simulation & Live Trading

*   **Offline Simulation**: Since Railway doesn't persist files across restarts by default (unless you add a Volume), the "Cached Data" mode might be limited. However, for live trading with Alpaca, it works perfectly.
*   **Live Trading**: Use the "Start Live" button on your deployed dashboard.

## Troubleshooting

*   **Build Errors**: Check the "Build Logs" in Railway. If a package is missing, add it to `requirements.txt` and push to GitHub.
*   **Runtime Errors**: Check "Deploy Logs".
*   **Database**: For persistent history in a production environment, you might want to add a PostgreSQL database service in Railway and update your config to use it, but for now, the file-based SQLite/JSON storage is fine for ephemeral sessions.

