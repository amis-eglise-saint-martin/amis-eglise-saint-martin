#!/usr/bin/env python3
"""
Build script for Église Saint-Martin website.

Injects header.html and footer.html into all HTML pages at build time,
and replaces {{PLACEHOLDER}} patterns with environment variable values.

Usage:
    python build.py               # Build to dist/ folder (staging mode, blocks crawlers)
    python build.py --production  # Build for production (allows crawlers)
    python build.py --watch       # Watch for changes and rebuild
    python build.py --clean       # Remove dist/ folder

Environment variables (for placeholder replacement):
    DOMAIN          - Site domain (required)
    CONTACT_EMAIL   - Contact email address (required)
    CONTACT_PHONE   - Contact phone number (required)
    FACEBOOK_URL    - Facebook page URL (required)
    GITHUB_URL      - GitHub repository URL (required)
    FORMSPREE_ID    - Formspree form ID (optional)
    VERSION         - Site version (optional, default: dev)

Project structure:
    src/            - Source HTML, CSS, JS, images
    dist/           - Built output (generated)
    docker/         - Docker deployment files
"""

import os
import re
import sys
import shutil
import hashlib
import argparse
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"
DIST_DIR = PROJECT_ROOT / "dist"
COMPONENTS_DIR = SRC_DIR / "components"

# Files/folders to copy as-is (not processed)
COPY_AS_IS = ["assets", "components"]

# SEO files
ROBOTS_STAGING = SRC_DIR / "robots.txt.staging"
ROBOTS_PRODUCTION = SRC_DIR / "robots.txt.production"
SITEMAP_FILE = SRC_DIR / "sitemap.xml"

# Markers in HTML files
HEADER_MARKER = '<div id="header"></div>'
FOOTER_MARKER = '<div id="footer"></div>'


def get_env_vars() -> dict:
    """Get configuration from environment variables."""
    # Required variables
    required = ['DOMAIN', 'CONTACT_EMAIL', 'CONTACT_PHONE', 'FACEBOOK_URL', 'GITHUB_URL']
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Set them in your environment or .env file")
        sys.exit(1)

    # CONTACT_PHONE_TEL: format for tel: href (e.g., +33612345678)
    # Auto-generate from CONTACT_PHONE if not provided
    phone = os.environ['CONTACT_PHONE']
    phone_tel = os.environ.get('CONTACT_PHONE_TEL', '')
    if not phone_tel:
        # Convert display format to tel format: "06 12 34 56 78" -> "+33612345678"
        digits = ''.join(c for c in phone if c.isdigit())
        if digits.startswith('0'):
            phone_tel = '+33' + digits[1:]
        else:
            phone_tel = '+' + digits

    return {
        'DOMAIN': os.environ['DOMAIN'],
        'CONTACT_EMAIL': os.environ['CONTACT_EMAIL'],
        'CONTACT_PHONE': phone,
        'CONTACT_PHONE_TEL': phone_tel,
        'FACEBOOK_URL': os.environ['FACEBOOK_URL'],
        'GITHUB_URL': os.environ['GITHUB_URL'],
        'FORMSPREE_ID': os.environ.get('FORMSPREE_ID', ''),
        'VERSION': os.environ.get('VERSION', 'dev'),
        'BUILD_MODE': os.environ.get('BUILD_MODE', 'staging'),
    }


def replace_placeholders(content: str, env_vars: dict) -> str:
    """Replace {{PLACEHOLDER}} patterns with environment variable values."""
    for key, value in env_vars.items():
        placeholder = f'{{{{{key}}}}}'  # {{KEY}}
        content = content.replace(placeholder, value)
    return content


def read_file(path: Path) -> str:
    """Read file content with UTF-8 encoding."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: Path, content: str) -> None:
    """Write content to file with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_file_hash(filepath: Path) -> str:
    """Compute a short MD5 hash of a file's content for cache busting."""
    content = filepath.read_bytes()
    return hashlib.md5(content).hexdigest()[:8]


def add_cache_busting(content: str) -> str:
    """Add ?v=HASH query strings to local asset references (CSS, JS, images, documents)."""
    def replace_asset_ref(match):
        attr = match.group(1)  # href= or src=
        quote = match.group(2)  # quote character
        path = match.group(3)  # e.g. /assets/css/custom.css
        # Strip leading slash for filesystem lookup
        clean_path = path.lstrip('/')
        filepath = SRC_DIR / clean_path
        if filepath.exists():
            file_hash = get_file_hash(filepath)
            return f'{attr}{quote}{path}?v={file_hash}{quote}'
        return match.group(0)

    # Match href= or src= pointing to local asset folders (with optional leading /)
    pattern = r'((?:href|src)=)(["\'])(/?assets/(?:css|js|images|documents)/[^"\'?]+)\2'
    return re.sub(pattern, replace_asset_ref, content)


def load_components(env_vars: dict) -> tuple[str, str]:
    """Load header and footer components with placeholder replacement."""
    header_path = COMPONENTS_DIR / "header.html"
    footer_path = COMPONENTS_DIR / "footer.html"

    if not header_path.exists():
        print(f"ERROR: {header_path} not found!")
        sys.exit(1)
    if not footer_path.exists():
        print(f"ERROR: {footer_path} not found!")
        sys.exit(1)

    header = replace_placeholders(read_file(header_path), env_vars)
    footer = replace_placeholders(read_file(footer_path), env_vars)

    return header, footer


def process_html(content: str, header: str, footer: str, filename: str, env_vars: dict) -> str:
    """
    Process an HTML file:
    1. Replace {{PLACEHOLDER}} patterns with env values
    2. Replace header marker with actual header content
    3. Replace footer marker with actual footer content
    4. Add active page marker to navigation
    """
    # Replace placeholders first
    processed = replace_placeholders(content, env_vars)

    # Get page name for active link marking
    page_name = Path(filename).stem  # e.g., "index", "contact", "historique"

    # Replace markers with actual content
    processed = processed.replace(HEADER_MARKER, f"<!-- HEADER -->\n{header}\n<!-- /HEADER -->")
    processed = processed.replace(FOOTER_MARKER, f"<!-- FOOTER -->\n{footer}\n<!-- /FOOTER -->")

    # Mark active page in navigation
    # Find links with data-page attribute matching current page
    pattern = rf'(<a[^>]*data-page="{page_name}"[^>]*>)([^<]*)(</a>)'

    def mark_active(match):
        opening = match.group(1)
        text = match.group(2)
        closing = match.group(3)
        # Add active class and bold text
        if 'class="' in opening:
            opening = opening.replace('class="', 'class="active ')
        else:
            opening = opening.replace('>', ' class="active">')
        return f'{opening}<strong>{text}</strong>{closing}'

    processed = re.sub(pattern, mark_active, processed)

    # Add cache-busting hashes to local CSS/JS references
    processed = add_cache_busting(processed)

    return processed


def clean_dist():
    """Remove the dist directory."""
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
        print(f"Cleaned: {DIST_DIR}")


def build(production_mode: bool = False):
    """Build the site: process HTML files and copy assets."""
    mode = "PRODUCTION" if production_mode else "STAGING"
    print(f"Building site... ({mode} mode)")

    # Get environment variables
    env_vars = get_env_vars()
    print(f"Domain: {env_vars['DOMAIN']}")

    # Check source directory exists
    if not SRC_DIR.exists():
        print(f"ERROR: Source directory {SRC_DIR} not found!")
        sys.exit(1)

    # Clean previous build
    clean_dist()

    # Load components (with placeholder replacement)
    header, footer = load_components(env_vars)
    print(f"Loaded components from {COMPONENTS_DIR}")

    # Create dist directory
    DIST_DIR.mkdir(exist_ok=True)

    # Process HTML files (recursive, excluding COPY_AS_IS directories)
    html_files = []
    for html_file in SRC_DIR.rglob("*.html"):
        relative = html_file.relative_to(SRC_DIR)
        if not any(relative.parts[0] == folder for folder in COPY_AS_IS):
            html_files.append(html_file)
    processed_count = 0

    for html_file in sorted(html_files):
        content = read_file(html_file)
        relative_path = html_file.relative_to(SRC_DIR)

        # Check if file has markers
        if HEADER_MARKER in content or FOOTER_MARKER in content:
            processed = process_html(content, header, footer, html_file.name, env_vars)
            write_file(DIST_DIR / relative_path, processed)
            print(f"  Processed: {relative_path}")
            processed_count += 1
        else:
            # Still apply placeholder replacement
            processed = replace_placeholders(content, env_vars)
            write_file(DIST_DIR / relative_path, processed)
            print(f"  Copied: {relative_path}")

    # Copy assets
    for folder in COPY_AS_IS:
        src = SRC_DIR / folder
        if src.exists():
            dst = DIST_DIR / folder
            if src.is_dir():
                shutil.copytree(src, dst)
                print(f"  Copied folder: {folder}/")
            else:
                shutil.copy2(src, dst)
                print(f"  Copied: {folder}")

    # Copy SEO files with placeholder replacement
    # robots.txt - choose based on production mode
    robots_src = ROBOTS_PRODUCTION if production_mode else ROBOTS_STAGING
    if robots_src.exists():
        robots_content = read_file(robots_src)
        robots_content = replace_placeholders(robots_content, env_vars)
        write_file(DIST_DIR / "robots.txt", robots_content)
        print(f"  Processed: robots.txt ({mode.lower()})")

    # sitemap.xml - apply placeholder replacement for domain
    if SITEMAP_FILE.exists():
        sitemap_content = read_file(SITEMAP_FILE)
        sitemap_content = replace_placeholders(sitemap_content, env_vars)
        write_file(DIST_DIR / "sitemap.xml", sitemap_content)
        print(f"  Processed: sitemap.xml")

    print(f"\nBuild complete!")
    print(f"  - Processed {processed_count} HTML files")
    print(f"  - Output: {DIST_DIR}/")
    if not production_mode:
        print(f"\nNote: Staging mode - search engines blocked via robots.txt")


def watch():
    """Watch for changes and rebuild automatically."""
    import time
    from datetime import datetime

    print("Watching for changes... (Ctrl+C to stop)")

    # Track file modification times
    last_mtimes = {}

    def get_mtimes():
        mtimes = {}
        # Watch HTML files (recursive, excluding COPY_AS_IS)
        for f in SRC_DIR.rglob("*.html"):
            relative = f.relative_to(SRC_DIR)
            if not any(relative.parts[0] == folder for folder in COPY_AS_IS):
                mtimes[f] = f.stat().st_mtime
        # Watch CSS
        css_dir = SRC_DIR / "assets" / "css"
        if css_dir.exists():
            for f in css_dir.glob("*.css"):
                mtimes[f] = f.stat().st_mtime
        return mtimes

    # Initial build
    build()
    last_mtimes = get_mtimes()

    while True:
        time.sleep(1)
        current_mtimes = get_mtimes()

        changed = []
        for f, mtime in current_mtimes.items():
            if f not in last_mtimes or last_mtimes[f] != mtime:
                changed.append(f)

        if changed:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Changes detected:")
            for f in changed:
                print(f"  - {f.name}")
            build()
            last_mtimes = current_mtimes


def main():
    parser = argparse.ArgumentParser(
        description="Build script for Église Saint-Martin website"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Watch for changes and rebuild automatically"
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Remove dist/ folder"
    )
    parser.add_argument(
        "--production", "-p",
        action="store_true",
        help="Build for production (allows search engine crawlers)"
    )

    args = parser.parse_args()

    if args.clean:
        clean_dist()
    elif args.watch:
        watch()
    else:
        build(production_mode=args.production)


if __name__ == "__main__":
    main()
