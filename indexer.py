import sqlite3 # To Pull metadata off the map.db file
import os
import re
import sys
import argparse # For the CLI inputs/.bat file implementation
from datetime import datetime
from pathlib import Path
from whoosh import index # The native Python equivalent to PyLucence (no Java VM required)
from whoosh.fields import DATETIME, ID, NUMERIC, Schema, TEXT # Builds the inverted index
from bs4 import BeautifulSoup # Parses HTML of the crawled pages i.e. Selenium


# This is key of whoosh over PyLucene, uses a simple schema definition 
# to replicate a Java-style documents (I've never used Java before tbh -Mario)
# FieldTypes imported above and configured in-line below.
#   Snippet is the first 300 chars of the Body
#   Body text field is not stored, just indexed
SCHEMA = Schema(
    url=ID(stored=True, unique=True),
    url_hash=ID(stored=True),
    title=TEXT(stored=True),
    body=TEXT(stored=False),
    snippet=TEXT(stored=True),
    crawl_date=DATETIME(stored=True),
    depth=NUMERIC(stored=True),
)

# Both opens existing indexes or makes new ones
#   The return type (index.Index) is an whoosh object 
#   that does everything we need to manage the indices
def open_or_create_index(index_dir: str) -> index.Index:

    os.makedirs(index_dir, exist_ok=True)
    if index.exists_in(index_dir):
        print(f"[indexer] Opening existing index at '{index_dir}'")
        return index.open_dir(index_dir)
    print(f"[indexer] Creating new index at '{index_dir}'")
    return index.create_in(index_dir, SCHEMA)

# Grabs the associated metadata from the map.db file for indexing
#   Contains our SQL query to retrieve the metadata, shouldn't need to be changed
def load_db_metadata(db_path: str) -> dict:
    metadata = {}
    if not os.path.isfile(db_path):
        print(f"[indexer] WARNING: map.db not found at '{db_path}'."
              "Metadata (URL, date, and depth fields) will be unavailable.")
        return metadata
    
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT url, date, depth, hash FROM visited")
    for url, date_str, depth, url_hash in cur.fetchall():
        try:
            crawl_date = datetime.fromisoformat(date_str)
        except Exception:
            crawl_date = datetime.now()
        metadata[url_hash] = {
            "url": url,
            "crawl_date": crawl_date,
            "depth": depth or 0,
        }
    con.close()
    print(f"[indexer] Loaded metadata for {len(metadata)} URLs from map.db")
    return metadata

# Get rid of all the html formatting noise and store the text from pages
def extract_html_fields(html_bytes: bytes) -> dict:
    good_soup = BeautifulSoup(html_bytes, "html.parser")

    title_tag = good_soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # decompose actually destroys the html elements we don't care about 
    # Then we manually strip the ws from the body and build the snippet
    for tag in good_soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    raw_text = good_soup.get_text(separator=" ")
    body = re.sub(r"\s+", " ", raw_text).strip()

    snippet = body[:300].rsplit(" ", 1)[0] + "…" if len(body) > 300 else body

    return {"title": title, "body": body, "snippet": snippet}

# The Inverted Index builder
# Loads all the metadata, associates it with the text fields, and writes it all to a whoosh index object
#   All fields have a default, so it should keep chugging along even if something is missing
#   If crawl_date not found, defaults to right now
#   No return type, index is written to the 'index_dir'
def build_index(crawled_dir: str, index_dir: str, db_path: str):
    idx = open_or_create_index(index_dir)
    metadata = load_db_metadata(db_path)

    html_files = list(Path(crawled_dir).glob("*.html"))
    if not html_files:
        print(f"[indexer] No .html files found in '{crawled_dir}'."
              "It's a disaster. Try scrawling_crawler again?")
        sys.exit(1)

    print(f"[indexer] Found {len(html_files)} HTML files to index...")

    writer = idx.writer()
    indexed = 0
    skipped = 0

    for filepath in html_files:
        url_hash = filepath.stem
        meta = metadata.get(url_hash, {})

        url = meta.get("url", filepath.name)
        crawl_date = meta.get("crawl_date", datetime.now())
        depth = meta.get("depth", 0)

        try:
            html_bytes = filepath.read_bytes()
            fields = extract_html_fields(html_bytes)
        except Exception as e:
            print(f"[indexer] SKIP {filepath.name}: {e}")
            skipped += 1
            continue

        # Idea is that if a page has < 50 chars, its an error, stub, redirect etc.
        if len(fields["body"]) < 50:
            skipped += 1
            continue

        writer.update_document(
            url=url,
            url_hash=url_hash,
            title=fields["title"] or url,
            body=fields["body"],
            snippet=fields["snippet"],
            crawl_date=crawl_date,
            depth=depth,
        )
        indexed += 1

        if indexed % 100 == 0:
            print(f"[indexer] Indexed {indexed}/{len(html_files)}...")

    writer.commit()
    print(f"\n[indexer] Done, Indexed: {indexed} | Skipped: {skipped}")
    print(f"[indexer] Index written to '{index_dir}'")

# Command Line Interface, should work with .bat file as well
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Part B1: HTML Indexer")
    parser.add_argument("crawled_dir", help="Folder of .html files from scrawling_crawler", default="crawled_pages", nargs="?")
    parser.add_argument("index_dir", help="Output folder for inverted index", default="index", nargs="?")
    parser.add_argument("db_path", nargs="?", default="map.db",
                        help="Path to map.db from scrawling_crawler (default: map.db)")
    args = parser.parse_args()

    build_index(args.crawled_dir, args.index_dir, args.db_path)