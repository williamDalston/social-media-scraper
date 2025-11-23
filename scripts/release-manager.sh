#!/bin/bash

# Release Management Script
# Manages application releases and versioning

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RELEASE_NOTES_DIR="${PROJECT_DIR}/releases"

# Create directories
mkdir -p "$RELEASE_NOTES_DIR"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to get current version
get_current_version() {
    if [ -f "${PROJECT_DIR}/VERSION" ]; then
        cat "${PROJECT_DIR}/VERSION"
    elif command -v git &> /dev/null && [ -d "${PROJECT_DIR}/.git" ]; then
        git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0"
    else
        echo "0.0.0"
    fi
}

# Function to bump version
bump_version() {
    local current_version=$(get_current_version)
    local bump_type=${1:-patch}
    
    # Parse version
    IFS='.' read -ra VERSION_PARTS <<< "$current_version"
    local major=${VERSION_PARTS[0]:-0}
    local minor=${VERSION_PARTS[1]:-0}
    local patch=${VERSION_PARTS[2]:-0}
    
    # Bump version
    case "$bump_type" in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            error "Invalid bump type: $bump_type (use: major, minor, patch)"
            return 1
            ;;
    esac
    
    local new_version="${major}.${minor}.${patch}"
    echo "$new_version"
}

# Function to create release
create_release() {
    local version=$1
    local release_notes=${2:-}
    
    if [ -z "$version" ]; then
        error "Version required"
        return 1
    fi
    
    log "Creating release: $version"
    
    # Create release notes file
    local notes_file="${RELEASE_NOTES_DIR}/RELEASE-${version}.md"
    {
        echo "# Release ${version}"
        echo ""
        echo "**Release Date**: $(date +'%Y-%m-%d')"
        echo ""
        echo "## Changes"
        echo ""
        if [ -n "$release_notes" ]; then
            echo "$release_notes"
        else
            echo "See git log for changes."
        fi
        echo ""
        echo "## Deployment"
        echo ""
        echo "To deploy this release:"
        echo "\`\`\`bash"
        echo "export VERSION=${version}"
        echo "./scripts/deploy.sh"
        echo "\`\`\`"
    } > "$notes_file"
    
    # Update VERSION file
    echo "$version" > "${PROJECT_DIR}/VERSION"
    
    # Create git tag (if in git repo)
    if command -v git &> /dev/null && [ -d "${PROJECT_DIR}/.git" ]; then
        git add "${PROJECT_DIR}/VERSION" "$notes_file"
        git commit -m "Release ${version}" || true
        git tag -a "v${version}" -m "Release ${version}" || true
        log "Git tag created: v${version}"
    fi
    
    log "Release created: $version"
    log "Release notes: $notes_file"
}

# Function to list releases
list_releases() {
    log "Available releases:"
    
    if [ -f "${PROJECT_DIR}/VERSION" ]; then
        info "Current version: $(get_current_version)"
    fi
    
    if [ -d "$RELEASE_NOTES_DIR" ]; then
        ls -1t "$RELEASE_NOTES_DIR"/RELEASE-*.md 2>/dev/null | head -10 | while read file; do
            local version=$(basename "$file" | sed 's/RELEASE-\(.*\)\.md/\1/')
            local date=$(grep "Release Date" "$file" | cut -d: -f2 | xargs)
            echo "  - $version ($date)"
        done
    fi
}

# Function to show release notes
show_release_notes() {
    local version=$1
    
    if [ -z "$version" ]; then
        version=$(get_current_version)
    fi
    
    local notes_file="${RELEASE_NOTES_DIR}/RELEASE-${version}.md"
    
    if [ -f "$notes_file" ]; then
        cat "$notes_file"
    else
        error "Release notes not found for version: $version"
        return 1
    fi
}

# Main command handler
case "${1:-help}" in
    create)
        local bump_type=${2:-patch}
        local current_version=$(get_current_version)
        local new_version=$(bump_version "$bump_type")
        
        log "Bumping version: $current_version -> $new_version"
        create_release "$new_version" "${3:-}"
        ;;
    bump)
        local bump_type=${2:-patch}
        local new_version=$(bump_version "$bump_type")
        echo "$new_version"
        ;;
    current)
        get_current_version
        ;;
    list)
        list_releases
        ;;
    notes)
        show_release_notes "${2:-}"
        ;;
    *)
        echo "Usage: $0 {create|bump|current|list|notes} [args]"
        echo ""
        echo "Commands:"
        echo "  create [major|minor|patch] [notes] - Create a new release"
        echo "  bump [major|minor|patch]            - Bump version and return new version"
        echo "  current                             - Show current version"
        echo "  list                                - List all releases"
        echo "  notes [version]                     - Show release notes"
        exit 1
        ;;
esac

