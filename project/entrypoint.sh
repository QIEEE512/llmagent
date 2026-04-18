#!/bin/bash

app_env=${1:-development}

PORT=8080

check_port_in_use() {
    if command -v ss >/dev/null 2>&1; then
        ss -ltnp 2>/dev/null | grep -q ":${PORT} " && return 0 || return 1
    fi
    if command -v lsof >/dev/null 2>&1; then
        lsof -i :${PORT} -sTCP:LISTEN -Pn >/dev/null 2>&1 && return 0 || return 1
    fi
    return 1
}

print_port_owner() {
    echo "[entrypoint] port ${PORT} is already in use. owner:" >&2
    if command -v ss >/dev/null 2>&1; then
        ss -ltnp 2>/dev/null | grep ":${PORT} " >&2 || true
    fi
    if command -v lsof >/dev/null 2>&1; then
        lsof -i :${PORT} -sTCP:LISTEN -Pn >&2 || true
    fi
}

if check_port_in_use; then
    print_port_owner
    exit 98
fi

# Prefer activating Python virtual environment if present
if [ -f "bin/activate" ]; then
    . bin/activate
fi

# Development environment commands
dev_commands() {
    echo "Running development environment commands..."
    python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
}

# Production environment commands
prod_commands() {
    echo "Running production environment commands..."
    python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
}

# Decide environment based on argument
if [ "$app_env" = "production" ] || [ "$app_env" = "prod" ] ; then
    echo "Production environment detected"
    prod_commands
else
    echo "Development environment detected"
    dev_commands
fi
