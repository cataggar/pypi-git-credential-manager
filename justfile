# Show the current version
version:
    uvx --with hatch-vcs hatchling version

# Build wheels for a specific GCM version (e.g., just build 2.7.3)
build version:
    uv run scripts/build_wheels.py {{version}}

# Clean build artifacts
clean:
    rm -rf dist/
