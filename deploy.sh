#!/bin/bash
echo "🚀 Starting deployment..."

# 1. Pull latest code from GitHub
echo "📥 Pulling latest code..."
git pull origin main

# 2. Build the frontend
echo "🏗️ Building frontend..."
cd frontend
npm install
npm run build
cd ..

# 3. Restart the backend service
# (Uncomment the line below if you have a systemd service set up for your backend)
# echo "🔄 Restarting backend..."
# sudo systemctl restart ams-backend

echo "✅ Deployment completed successfully!"
