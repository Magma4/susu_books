#!/usr/bin/env bash
# =============================================================================
# Susu Books — One-Command Setup Script
# Checks dependencies, ensures Gemma 4 is available in Ollama, seeds demo data,
# and starts the app with Docker or local development tooling.
#
# Usage:
#   bash setup.sh
#   bash setup.sh --dev
#   bash setup.sh --no-docker
#   bash setup.sh --no-seed
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

NO_DOCKER=false
NO_SEED=false
DEV_MODE=false

for arg in "$@"; do
  case "$arg" in
    --no-docker) NO_DOCKER=true ;;
    --no-seed) NO_SEED=true ;;
    --dev) DEV_MODE=true ;;
    *)
      echo -e "${RED}Unknown option:${NC} $arg"
      exit 1
      ;;
  esac
done

PREFERRED_MODEL="gemma4:31b-instruct"
MOE_MODEL="gemma4:26b-a4b-instruct"
EDGE_MODEL="gemma4:e2b"
OLLAMA_MODEL="$PREFERRED_MODEL"

print_header() {
  echo ""
  echo -e "${GREEN}${BOLD}╔══════════════════════════════════════╗${NC}"
  echo -e "${GREEN}${BOLD}║       📒 Susu Books Setup            ║${NC}"
  echo -e "${GREEN}${BOLD}║   Voice-First Business Copilot       ║${NC}"
  echo -e "${GREEN}${BOLD}╚══════════════════════════════════════╝${NC}"
  echo ""
}

step() { echo -e "${BLUE}${BOLD}▶ $1${NC}"; }
ok() { echo -e "${GREEN}  ✓ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
fail() { echo -e "${RED}  ✗ $1${NC}"; }
info() { echo -e "${CYAN}  → $1${NC}"; }

wait_for_url() {
  local url="$1"
  local timeout_seconds="${2:-60}"
  local label="${3:-service}"
  local start_ts
  start_ts=$(date +%s)

  until curl -sf "$url" >/dev/null 2>&1; do
    if [ $(( $(date +%s) - start_ts )) -ge "$timeout_seconds" ]; then
      fail "Timed out waiting for $label at $url"
      return 1
    fi
    sleep 2
  done

  ok "$label is ready"
}

check_ollama() {
  step "Checking Ollama installation"

  if ! command -v ollama >/dev/null 2>&1; then
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

  if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    warn "Ollama server is not running. Starting it..."
    nohup ollama serve >/tmp/susu-books-ollama.log 2>&1 &
    sleep 3
  fi

  if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    fail "Could not reach Ollama at http://localhost:11434. Please run 'ollama serve' and retry."
    exit 1
  fi

  ok "Ollama server is running at http://localhost:11434"
}

pick_or_pull_model() {
  step "Checking Gemma 4 model availability"

  local available
  available=$(curl -sf http://localhost:11434/api/tags | python3 -c '
import json, sys
data = json.load(sys.stdin)
print(" ".join(model.get("name", "") for model in data.get("models", [])))
' 2>/dev/null || echo "")

  if echo "$available" | grep -q "$PREFERRED_MODEL"; then
    OLLAMA_MODEL="$PREFERRED_MODEL"
    ok "Found preferred model: $OLLAMA_MODEL"
    return
  fi

  if echo "$available" | grep -q "$MOE_MODEL"; then
    OLLAMA_MODEL="$MOE_MODEL"
    ok "Found Gemma 4 MoE fallback: $OLLAMA_MODEL"
    return
  fi

  if echo "$available" | grep -q "$EDGE_MODEL"; then
    OLLAMA_MODEL="$EDGE_MODEL"
    warn "Using lightweight fallback already installed: $OLLAMA_MODEL"
    return
  fi

  echo ""
  echo -e "  ${BOLD}No Gemma 4 model found locally. Pulling the best available option...${NC}"
  echo -e "  ${YELLOW}Preferred:${NC} $PREFERRED_MODEL"
  echo -e "  ${YELLOW}Fallbacks:${NC} $MOE_MODEL, $EDGE_MODEL"
  echo ""

  if ollama pull "$PREFERRED_MODEL"; then
    OLLAMA_MODEL="$PREFERRED_MODEL"
  elif ollama pull "$MOE_MODEL"; then
    OLLAMA_MODEL="$MOE_MODEL"
  else
    warn "Falling back to the smallest Gemma 4 variant for this machine."
    ollama pull "$EDGE_MODEL"
    OLLAMA_MODEL="$EDGE_MODEL"
  fi

  ok "Model ready: $OLLAMA_MODEL"
}

write_backend_env() {
  step "Preparing backend environment"

  if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    ok "Created backend/.env from backend/.env.example"
  fi

  if grep -q '^OLLAMA_MODEL=' backend/.env; then
    sed -i.bak "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=$OLLAMA_MODEL/" backend/.env
  else
    printf '\nOLLAMA_MODEL=%s\n' "$OLLAMA_MODEL" >> backend/.env
  fi

  if grep -q '^OLLAMA_BASE_URL=' backend/.env; then
    sed -i.bak "s|^OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=http://localhost:11434|" backend/.env
  else
    printf 'OLLAMA_BASE_URL=http://localhost:11434\n' >> backend/.env
  fi

  if grep -q '^OLLAMA_TIMEOUT=' backend/.env; then
    sed -i.bak "s/^OLLAMA_TIMEOUT=.*/OLLAMA_TIMEOUT=300/" backend/.env
  else
    printf 'OLLAMA_TIMEOUT=300\n' >> backend/.env
  fi

  if ! grep -q '^ENVIRONMENT=' backend/.env; then
    printf 'ENVIRONMENT=development\n' >> backend/.env
  fi

  if ! grep -q '^API_DOCS_ENABLED=' backend/.env; then
    printf 'API_DOCS_ENABLED=true\n' >> backend/.env
  fi

  if ! grep -q '^SECURITY_HEADERS_ENABLED=' backend/.env; then
    printf 'SECURITY_HEADERS_ENABLED=true\n' >> backend/.env
  fi

  if ! grep -q '^ALLOWED_HOSTS=' backend/.env; then
    printf 'ALLOWED_HOSTS=localhost,127.0.0.1\n' >> backend/.env
  fi

  if ! grep -q '^CORS_ORIGINS=' backend/.env; then
    printf 'CORS_ORIGINS=http://localhost:3000\n' >> backend/.env
  fi

  rm -f backend/.env.bak
  ok "Configured backend to use $OLLAMA_MODEL"
}

setup_backend_dev() {
  step "Setting up Python backend"
  cd backend

  if [ ! -d ".venv" ]; then
    info "Creating Python virtual environment..."
    python3 -m venv .venv
  fi

  # shellcheck disable=SC1091
  source .venv/bin/activate
  info "Installing Python dependencies..."
  pip install -q -r requirements.txt
  ok "Backend dependencies installed"

  cd ..
}

setup_frontend_dev() {
  step "Setting up Next.js frontend"
  cd frontend

  if ! command -v node >/dev/null 2>&1; then
    fail "Node.js not found. Install Node.js 20+ from https://nodejs.org."
    exit 1
  fi

  ok "Node.js: $(node --version)"
  info "Installing npm dependencies..."
  npm install --silent
  ok "Frontend dependencies installed"

  if [ ! -f ".env.local" ]; then
    printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\n' > .env.local
    ok "Created frontend/.env.local"
  fi

  cd ..
}

seed_database_local() {
  step "Seeding database with demo data"
  cd backend
  if [ -d ".venv" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
  fi
  python3 seed.py
  ok "Database seeded with Ama's two-week market history"
  cd ..
}

start_docker() {
  step "Starting Susu Books with Docker Compose"

  if ! command -v docker >/dev/null 2>&1; then
    fail "Docker not found. Install Docker Desktop or Docker Engine first."
    exit 1
  fi

  if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
  elif docker-compose version >/dev/null 2>&1; then
    DC="docker-compose"
  else
    fail "Docker Compose not found."
    exit 1
  fi

  info "Building containers..."
  OLLAMA_MODEL="$OLLAMA_MODEL" $DC build

  info "Starting services..."
  OLLAMA_MODEL="$OLLAMA_MODEL" $DC up -d

  wait_for_url "http://localhost:8000/api/health" 90 "backend"

  if [ "$NO_SEED" = false ]; then
    step "Seeding database via Docker"
    docker exec susu-backend python seed.py
    ok "Database seeded in Docker volume"
  fi

  echo ""
  echo -e "  ${BOLD}Frontend:${NC} ${CYAN}http://localhost:3000${NC}"
  echo -e "  ${BOLD}Backend:${NC}  ${CYAN}http://localhost:8000${NC}"
  echo -e "  ${BOLD}API Docs:${NC} ${CYAN}http://localhost:8000/docs${NC} ${YELLOW}(if enabled)${NC}"
  echo ""
  echo -e "  Stop with: ${BOLD}$DC down${NC}"
}

start_dev() {
  step "Starting Susu Books in development mode"

  cd backend
  # shellcheck disable=SC1091
  source .venv/bin/activate
  info "Starting FastAPI backend on port 8000..."
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
  BACKEND_PID=$!
  cd ..

  wait_for_url "http://localhost:8000/api/health" 60 "backend"

  cd frontend
  info "Starting Next.js frontend on port 3000..."
  npm run dev &
  FRONTEND_PID=$!
  cd ..

  echo ""
  echo -e "  ${BOLD}Frontend:${NC} ${CYAN}http://localhost:3000${NC}"
  echo -e "  ${BOLD}Backend:${NC}  ${CYAN}http://localhost:8000${NC}"
  echo -e "  ${BOLD}API Docs:${NC} ${CYAN}http://localhost:8000/docs${NC} ${YELLOW}(if enabled)${NC}"
  echo ""
  echo -e "  Press ${BOLD}Ctrl+C${NC} to stop both servers"

  trap 'kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true; exit' INT TERM
  wait
}

print_header
check_ollama
pick_or_pull_model
write_backend_env

if [ "$NO_DOCKER" = true ] || [ "$DEV_MODE" = true ]; then
  setup_backend_dev
  setup_frontend_dev

  if [ "$NO_SEED" = false ]; then
    seed_database_local
  fi

  start_dev
else
  start_docker
fi
