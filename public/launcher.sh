#!/usr/bin/env bash

echo "LaTeX Calc - Desktop Engine Launcher (Mac/Linux)"
echo "================================================"
echo ""

# 1. Find Julia Executable
JULIA_CMD=""

if command -v julia >/dev/null 2>&1; then
    JULIA_CMD="julia"
else
    # Check common macOS installation paths
    # usually /Applications/Julia-1.10.app/Contents/Resources/julia/bin/julia
    # We will search for any Julia app in /Applications
    for app in /Applications/Julia-*.app; do
        if [ -x "$app/Contents/Resources/julia/bin/julia" ]; then
            JULIA_CMD="$app/Contents/Resources/julia/bin/julia"
            break
        fi
    done
    
    if [ -z "$JULIA_CMD" ] && [ -x "/Applications/Julia.app/Contents/Resources/julia/bin/julia" ]; then
        JULIA_CMD="/Applications/Julia.app/Contents/Resources/julia/bin/julia"
    fi
fi

if [ -z "$JULIA_CMD" ]; then
    echo "ERROR: Could not find 'julia' in PATH or default macOS install locations."
    echo "Please install Julia from https://julialang.org/downloads/"
    echo "and ensure it is added to your PATH."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# 2. Check and Install Packages
echo "Verifying Julia packages..."
"$JULIA_CMD" -e 'using Pkg; installed=[p.name for p in values(Pkg.dependencies())]; for p in ["HTTP", "JSON3", "SymPy", "Roots"]; p in installed || Pkg.add(p); end'

echo ""
echo "Starting Desktop Engine..."
"$JULIA_CMD" server.jl

echo ""
echo "Desktop Engine has crashed or terminated."
read -p "Press Enter to exit..."
