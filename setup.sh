#!/usr/bin/env bash
# =============================================================================
# Susu Books — One-Command Setup Script
# Checks all dependencies, pulls Gemma 4, seeds the database, and starts the app.
# Usage: bash setup.sh [--no-docker] [--no-seed] [--dev]
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Flags
NO_DOCKER=false
NO_SEED=false
DEV_MODE=false

for arg in "$@"; do
  case $arg in
    --no-docker) NO_DOCKER=true ;;
    --no-seed)   NO_SEED=true ;;
    --dev)       DEV_MODE=true ;;
  esac
done

OLLAMA_MODEL="gemma4:31b-instruct"
OLLAMA_MODEL_LITE="gemma4:26b-a4b-instruct"

# =============================================================================
print_header() {
  echo ""
  echo -e "${GREEN}${BOLD}╔══════════════════════════════════════╗${NC}"
  echo -e "${GREEN}${BOLD}║       📒 Susu Books Setup            ║${NC}"
  echo -e "${GREEN}${BOLD}║   Voice-First Business Copilot       ║${NC}"
  echo -e "${GREEN}${BOLD}╚══════════════════════════════════════╝${NC}"
  echo ""
}

step() { echo -e "${BLUE}${BOLD}▶ $1${NC}"; }
ok()   { echo -e "${GREEN}  ✓ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
fail() { echo -e "${RED}  ✗ $1${NC}"; }
info() { echo -e "${CYAN}  → $1${NC}"; }

# =============================================================================
# Check Ollama
# =============================================================================
check_ollama() {
  step "Checking Ollama installation"

  if ! command -v ollama &>/dev/null; then
    fail "Ollama is not installed."
    echo ""
    echo -e "  ${BOLD}Install Ollama:${NC}"
    echo "  macOS:   curl -fsSL https://ollama.ai/install.sh | sh"
    echo "  Linux:   curl -fsSL https://ollama.ai/install.sh | sh"
    echo "  Windows: https://ollama.ai/download"
    echo ""
    exit 1
  fi
  ok "Ollama binary found: $(ollama --version 2>/dev/null || echo 'installed')"

  # Check if Ollama server is running
  if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    warn "Ollama server is not running. Starting it..."
    ollama serve &>/dev/null &
    sleep 3
    if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
      fail "Could not start Ollama. Please run 'ollama serve' manually and retry."
      exit 1
    fi
    ok "Ollama server started"
  else
    ok "Ollama server is running at http://localhost:11434"
  fi
}

# =============================================================================
# Pull Gemma 4 model
# =============================================================================
pull_model() {
  step "Checking Gemma 4 model"

  AVAILABLE=$(curl -sf http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print(' '.join(models))
" 2>/dev/null || echo "")

  if echo "$AVAILABLE" | grep -q "gemma4:31b"; then
    ok "Gemma 4 31B already downloaded"
  elif echo "$AVAILABLE" | grep -q "gemma4:26b"; then
    ok "Gemma 4 26B MoE already downloaded (will use instead of 31B)"
    OLLAMA_MODEL="$OLLAMA_MODEL_LITE"
  else
    echo ""
    echo -e "  ${BOLD}Pulling $OLLAMA_MODEL (~20GB)...${NC}"
    echo -e "  ${YELLOW}This will take a while on first run.${NC}"
    echo ""

    # Try 31B first; fall back to lighter MoE variant
    if ! ollama pull "$OLLAMA_MODEL"; then
      warn "Failed to pull $OLLAMA_MODEL. Trying lighter MoE variant..."
      ollama pull "$OLLAMA_MODEL_LITE"
      OLLAMA_MODEL="$OLLAMA_MODEL_LITE"
    fi
    ok "Model downloaded: $OLLAMA_MODEL"

    # Update backend config to use the model that was pulled
    if [ -f "backend/.env" ]; then
      sed -i.bak "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=$OLLAMA_MODEL/" backend/.env
    fi
  fi
}

# =============================================================================
# Backend setup (no Docker)
# =============================================================================
setup_backend_dev() {
  step "Setting up Python backend"

  cd backend

  if [ ! -d ".venv" ]; then
    info "Creating Python virtual environment..."
    python3 -m venv .venv
  fi

  # Activate venv
  source .venv/bin/activate

  info "Installing Python dependencies..."
  pip install -q -r requirements.txt
  ok "Backend dependencies installed"

  # Create .env if missing
  if [ ! -f ".env" ]; then
    cat > .env <<EOF
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=$OLLAMA_MODEL
DATABASE_URL=sqlite:///susu_books.db
DEBUG=false
EOF
    ok ".env file created"
  fi

  cd ..
}

# =============================================================================
# Frontend setup (no Docker)
# =============================================================================
setup_frontend_dev() {
  step "Setting up Next.js frontend"

  cd frontend

  if ! command -v node &>/dev/null; then
    fail "Node.js not found. Install from https://nodejs.org (v20+ recommended)"
    exit 1
  fi
  ok "Node.js: $(node --version)"

  info "Installing npm dependencies..."
  npm install --silent
  ok "Frontend dependencies installed"

  # Create .env.local if missing
  if [ ! -f ".env.local" ]; then
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
    ok ".env.local created"
  fi

  cd ..
}

# =============================================================================
# Seed database
# =============================================================================
seed_database() {
  step "Seeding database with demo data"

  cd backend

  if [ -d ".venv" ]; then
    source .venv/bin/activate
  fi

  python3 seed.py && ok "Database seeded with 2 weeks of Ama's transactions" || warn "Seed failed (may already be seeded)"

  cd ..
}

# =============================================================================
# Start via Docker Compose
# =============================================================================
start_docker() {
  step "Starting Susu Books with Docker Compose"

  if ! command -v docker &>/dev/null; then
    fail "Docker not found. Install from https://docs.docker.com/get-docker/"
    exit 1
  fi

  if ! docker compose version &>/dev/null 2>&1 && ! docker-compose version &>/dev/null 2>&1; then
    fail "Docker Compose not found."
    exit 1
  fi

  # Use 'docker compose' (v2) or 'docker-compose' (v1)
  DC="docker compose"
  $DC version &>/dev/null 2>&1 || DC="docker-compose"

  info "Building containers (first run takes ~5 minutes)..."
  $DC build

  info "Starting services..."
  $DC up -d

  ok "Susu Books is running!"
  echo ""
  echo -e "  ${BOLD}Frontend:${NC} ${CYAN}http://localhost:3000${NC}"
  echo -e "  ${BOLD}Backend:${NC}  ${CYAN}http://localhost:8000${NC}"
  echo -e "  ${BOLD}API Docs:${NC} ${CYAN}http://localhost:8000/docs${NC}"
  echo ""
  echo -e "  Stop with: ${BOLD}docker compose down${NC}"
}

# =============================================================================
# Start in dev mode (no Docker)
# =============================================================================
start_dev() {
  step "Starting Susu Books in development mode"

  # Start backend in background
  info "Starting FastAPI backend on port 8000..."
  cd backend
  source .venv/bin/activate
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
  BACKEND_PID=$!
  cd ..

  # Give backend a moment to start
  sleep 2

  # Start frontend in background
  info "Starting Next.js frontend on port 3000..."
  cd frontend
  npm run dev &
  FRONTEND_PID=$!
  cd ..

  ok "Susu Books is running!"
  echo ""
  echo -e "  ${BOLD}Frontend:${NC} ${CYAN}http://localhost:3000${NC}"
  echo -e "  ${BOLD}Backend:${NC}  ${CYAN}http://localhost:8000${NC}"
  echo -e "  ${BOLD}API Docs:${NC} ${CYAN}http://localhost:8000/docs${NC}"
  echo ""
  echo -e "  Press ${BOLD}Ctrl+C${NC} to stop both servers"

  # Wait for interrupt
  trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
  wait
}

# =============================================================================
# Main
# =============================================================================
print_header

check_ollama
pull_model

if [ "$NO_DOCKER" = true ] || [ "$DEV_MODE" = true ]; then
  setup_backend_dev
  setup_frontend_dev
fi

if [ "$NO_SEED" = false ]; then
  if [ "$NO_DOCKER" = true ] || [ "$DEV_MODE" = true ]; then
    seed_database
  else
    # In Docker mode, seed after containers are built
    :
  fi
fi

if [ "$NO_DOCKER" = true ] || [ "$DEV_MODE" = true ]; then
  start_dev
else
  start_docker
  # Seed via Docker exec once the backend is healthy
  if [ "$NO_SEED" = false ]; then
    step "Seeding database via Docker"
    sleep 5  # let the backend fully start
    docker exec susu-backend python seed.py && ok "Database seeded" || warn "Seed skipped (already seeded)"
  fi
fi
