# Deployment Guide - Render.com

This guide will help you deploy the Canteen Ordering System to Render.com (a free backend hosting service).

## Prerequisites
- GitHub account (to push your code)
- Render.com account (free)

## Step-by-Step Deployment

### 1. Push Code to GitHub
```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit"

# Create a new repository on GitHub
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/canteen-ordering.git
git branch -M main
git push -u origin main
```

### 2. Create PostgreSQL Database on Render
1. Go to [Render.com](https://render.com)
2. Sign up for free account
3. Click "New +" → "PostgreSQL"
4. Create a free PostgreSQL instance (name: `canteen-db`)
5. Copy the database URL (you'll need this)

### 3. Deploy Flask App on Render
1. Click "New +" → "Web Service"
2. Select your GitHub repository
3. Configuration:
   - **Name**: `canteen-ordering-api`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free

4. Add Environment Variables:
   - `SECRET_KEY`: (generate a random string, e.g., `your-secret-key-here`)
   - `DATABASE_URL`: (paste the PostgreSQL URL from step 2)

5. Click "Create Web Service"

### 4. Wait for Deployment
- Deployment takes 2-3 minutes
- You'll get a URL like: `https://canteen-ordering-api.onrender.com`

## Using Your Deployed App

Your frontend can now access the backend at:
```
https://canteen-ordering-api.onrender.com
```

## Important Notes

- **Free tier limitations**: Render's free tier may go to sleep after 15 minutes of inactivity
- **Database**: PostgreSQL is included (free tier has limitations)
- **To upgrade**: Visit Render dashboard to upgrade to paid plans when needed

## Environment Variables

Make sure these are set on Render:
- `SECRET_KEY` - Your Flask secret key
- `DATABASE_URL` - Your PostgreSQL connection string

## Troubleshooting

**Error: Database connection failed**
- Check that DATABASE_URL is correctly set in Render environment variables
- Verify PostgreSQL instance is running

**Error: Module not found**
- Ensure all packages in requirements.txt are listed
- Check Python version compatibility

## Alternative Hosting Services

If you prefer other services:
- **Railway.app** - Similar to Render, often faster
- **Heroku** - Classic Python hosting (paid)
- **PythonAnywhere** - Beginner-friendly

For this app, we recommend **Render** or **Railway** for free tier.
