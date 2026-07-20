#!/bin/bash
echo "🚀 Starting deployment..."

echo "📥 Pulling latest code..."
git pull origin main

echo "🏗️ Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "🔄 Restarting backend..."
# Kill any existing python backend process
pkill -f "python run.py" || true
# Start the backend in the background
cd backend
nohup venv/bin/python run.py > backend.log 2>&1 &
cd ..

echo "✅ Deployment completed successfully!"
