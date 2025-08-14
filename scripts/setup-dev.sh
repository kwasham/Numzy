#!/bin/bash

# Setup script for development environment
set -e

echo "🚀 Setting up Numzy development environment..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "❌ pnpm is required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed."; exit 1; }

# Stop any existing containers first (root-level compose only)
echo "🛑 Stopping existing containers..."
docker compose down 2>/dev/null || true

# Create .env if it doesn't exist (root is the single source of truth)
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Environment
ENVIRONMENT=development

# Database (use Neon or local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/numzy

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Storage
STORAGE_BACKEND=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=receipts

# Auth
DEV_AUTH_BYPASS=true
CLERK_SECRET_KEY=your-clerk-secret-key

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
EOF
fi

# Do NOT copy .env into backend; the app loads the nearest .env automatically.

# Install dependencies
echo "📦 Installing dependencies..."
pnpm install

# Start shared infra
echo "🐳 Starting Docker infra (redis, minio)..."
docker compose --profile infra up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are healthy
echo "🔍 Checking service health..."
docker compose ps

echo "✅ Development environment setup complete!"
echo ""
echo "To start the application, run:"
echo "  pnpm dev"
echo ""
echo "Services available at:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - MinIO Console: http://localhost:9001"
echo "  - API Docs: http://localhost:8000/docs"