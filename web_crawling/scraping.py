
# Imports & Setup
from fileinput import filename
from firecrawl import Firecrawl
from dotenv import load_dotenv

import csv
import os
import time
import re
from urllib.parse import urljoin
import csv
import time
import json
from urllib.parse import urljoin

PROCESSED_FILE = "processed_products.json"
VISITED_URLS_FILE = "visited_urls.json"

def load_json_set(file_path):
    """Load a set from a JSON file safely."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure it's a list or set
            if isinstance(data, list):
                return set(data)
            elif isinstance(data, set):
                return data
            else:
                print(f"Warning: Unexpected JSON content in {file_path}. Starting fresh.")
                return set()
    except (FileNotFoundError, json.JSONDecodeError):
        # File missing or empty/corrupted JSON → start fresh
        return set()

def save_json_set(data_set, file_path):
    """Save a set to a JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(list(data_set), f, ensure_ascii=False, indent=2)
        
load_dotenv(override=True)
firecrawl = Firecrawl()

# ------------------------------
# File Saving Helper
# ------------------------------
def save_file(content, filename, dir_path="."):
    os.makedirs(dir_path, exist_ok=True)  # Create directory if it doesn't exist
    full_path = os.path.join(dir_path, filename)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved: {full_path}")
    return full_path
def is_pdf_url(url: str) -> bool:
    """
    True if URL/path points to a PDF, even with query or fragment.
    """
    if not url:
        return False

    clean = re.sub(r'[?#].*$', '', url)
    return clean.lower().endswith('.pdf')

# Content Cleaning
def remove_all_urls(content, pdf_extract=False):
    """
    Remove all URLs and markdown links from content.
    
    Args:
        content (str): The text content to clean.
        pdf_extract (bool): If True, keep PDF URLs in the content; else remove all URLs.
    
    Returns:
        str: Cleaned content.
    """
    if not content:
        return content

    # Remove markdown images completely
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)

    # Markdown links
    # [text](url) → keep text, unless pdf_extract=True and URL ends with .pdf
    if pdf_extract:
        content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)
    else:
        def _md_link_replacer(match):
            text, url = match.group(1), match.group(2)
            if pdf_extract:
                # pdf_extract=True → remove ALL URLs (including PDFs)
                return text
            else:
                # pdf_extract=False → keep PDFs (even with ? or #)
                return match.group(0) if is_pdf_url(url) else text
        content = re.sub(r'\[(.*?)\]\((.*?)\)', _md_link_replacer, content)
        
    content = re.sub(
        r'光学部材調達をさまざまな角度から迅速にサポート致します\s*[\r\n]+[-•*]\s*日本語\s*[\r\n]+[-•*]\s*English',
        '',
        content
    )
    # Remove plain URLs
    # Keep PDFs if pdf_extract=True
    if pdf_extract:
        # Remove all URLs, including PDFs
        content = re.sub(r'https?://\S+', '', content, flags=re.IGNORECASE)
        content = re.sub(r'ftp://\S+', '', content, flags=re.IGNORECASE)
        content = re.sub(r'www\.\S+', '', content, flags=re.IGNORECASE)
    else:
        # Keep PDFs (even with ? or #), remove everything else
        urls = re.findall(r'(https?://\S+|ftp://\S+|www\.\S+)', content)
        for url in urls:
            if not is_pdf_url(url):
                content = content.replace(url, '')

    # Remove emails
    content = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        '',
        content
    )

    # Line-wise cleanup
    cleaned_lines = []

    for line in content.splitlines():
        stripped = line.strip()

        # Skip meaningless lines
        if stripped in ['[]', '()', '{}', '⟨⟩', '「」', '『』', '【】']:
            continue

        # Skip file paths or remaining URLs (except PDF if pdf_extract=True)
        if re.match(r'^[./\\]', stripped) or '://' in stripped:
            if not pdf_extract and is_pdf_url(stripped):
                pass  # keep PDF paths/URLs (handles ? and #)
            else:
                continue

        # Remove non-PDF file references
        if not is_pdf_url(stripped):
            line = re.sub(
                r'\bhttps?://\S+\.(com|org|net|jp|co\.jp|io|gov|edu)([/?#]\S*)?\b',
                '',
                line,
                flags=re.IGNORECASE
            )
        line = re.sub(
            r'\S+\.(jpg|jpeg|png|gif|svg|mp4|avi|mov)\b',
            '',
            line,
            flags=re.IGNORECASE
        )
        if pdf_extract:
            # Remove PDFs only if truly non-PDF (handles ? and # safely)
            line = re.sub(r'\S+\.pdf([?#]\S+)?', '', line, flags=re.IGNORECASE)

        # Skip list markers
        if re.match(r'^[-*]\s*$', stripped) or re.match(r'^\d+\.\s*$', stripped):
            continue

        # Remove isolated punctuation
        line = re.sub(r'^[\[\](){}⟨⟩「」『』【】]*$', '', line)

        if line.strip():
            cleaned_lines.append(line)

    # Join lines and remove excessive blank lines
    content = '\n'.join(cleaned_lines)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

    return content.strip()

# PDF Link Extraction
def extract_pdf_links(markdown):
    """Extract PDF links from markdown content, including fragments."""
    links = []

    if not markdown:
        return links

    # Markdown links
    md_links = re.findall(r'\[.*?\]\((.*?)\)', markdown)
    for link in md_links:
        clean_link = re.sub(r'#.*', '', link)

        if clean_link.lower().endswith('.pdf'):
            if clean_link.startswith(('http://', 'https://', 'ftp://')):
                links.append(('pdf', clean_link))
            elif clean_link.startswith('/'):
                links.append(('pdf', clean_link))

    # Plain PDF URLs
    plain_pdf_urls = re.findall(
        r'https?://[^\s<>"]+\.pdf',
        markdown,
        re.IGNORECASE
    )
    for pdf_url in plain_pdf_urls:
        links.append(('pdf', re.sub(r'#.*', '', pdf_url)))

    # Deduplicate (order preserved)
    seen = set()
    unique_links = []

    for link_type, url in links:
        if url not in seen:
            seen.add(url)
            unique_links.append((link_type, url))

    return unique_links


def clean_pdf_url(url):
    """Clean PDF URL by removing fragments."""
    url = re.sub(r'#.*', '', url)
    return url.strip()


# Scraping Logic
def scrape_url(url, visited_urls, pdf_extractor=False):
    """Scrape a single URL and clean content."""
    if url in visited_urls:
        return None

    print(f"Scraping: {url}")
    visited_urls.add(url)

    try:
        doc = firecrawl.scrape(
            url,
            formats=["markdown"],
            only_main_content=False,
            exclude_tags=["nav", "globalheader", "footer"]
        )

        if not doc or not doc.markdown:
            print(f"No data returned for {url}")
            return None

        markdown = doc.markdown

        filename = re.sub(
            r'[^a-zA-Z0-9_]', '_',
            url.replace('https://', '').replace('http://', '')
        )[:50]

        save_file(f"# Source URL: {url}\n\n{markdown}", f"{filename}_row1.md", dir_path="scraped_raw")


        cleaned_content = remove_all_urls(markdown, pdf_extract=pdf_extractor)

        save_file(f"# Source URL: {url}\n\n{cleaned_content}", f"{filename}.md", dir_path="scraped_cleaned")

        print(f"Saved: {filename}.md")
        if pdf_extractor:
            extract_pdf_links(markdown)
        return  None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)[:100]}")
        return None


def scrape_pdf(url, visited_urls):
    """Handle PDF URL scraping."""
    if url in visited_urls:
        return

    print(f"Scraping PDF: {url}")
    visited_urls.add(url)

    try:
        doc = firecrawl.scrape(url, formats=["markdown"])
        markdown = doc.markdown

        filename = re.sub(
            r'[^a-zA-Z0-9_]', '_',
            url.replace('https://', '').replace('http://', '')
        )[:50]

        save_file(f"# Source URL: {url}\n\n{markdown}", f"{filename}_row_PDF.md", dir_path="pdf_raw")

        cleaned_content = remove_all_urls(markdown)

        save_file(f"# Source URL: {url}\n\n{cleaned_content}", f"{filename}_PDF.md", dir_path="pdf_cleaned")
        print(f"Saved PDF: {filename}_PDF.md")

    except Exception as e:
        print(f"Error scraping PDF {url}: {str(e)[:100]}")


# CSV Processing
def process_csv(csv_file_path, pdf_extractor=False):
    """Process URLs from CSV file."""
    visited_urls = set()
    visited_urls = load_json_set(VISITED_URLS_FILE)
    processed_products = load_json_set(PROCESSED_FILE)
    md_names = [os.path.splitext(f)[0] for f in os.listdir("scraped_cleaned") if f.lower().endswith(".md")]
    print(md_names)
    with open(csv_file_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            url = None

            for key in row:
                if key.lower() == "url" and row[key].strip():
                    url = row[key].strip()
                    break

            if not url:
                for key in row:
                    if row[key] and "http" in row[key].lower():
                        url = row[key].strip()
                        break

            if not url:
                continue

            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            filename = re.sub(
            r'[^a-zA-Z0-9_]', '_',
            url.replace('https://', '').replace('http://', '')
        )[:50]
            product_name = row[' Model']
            if filename in md_names:
                processed_products.add(product_name)
                visited_urls.add(url)
                print(f"Skipping already processed product by filename: {filename}")
                continue
            extracted_links = scrape_url(url, visited_urls,pdf_extractor=pdf_extractor)

            if pdf_extractor and extracted_links:
                for _, link_url in extracted_links:
                    if link_url.startswith("/"):
                        link_url = urljoin(url, link_url)
                    scrape_pdf(link_url, visited_urls)
            # Mark product as processed
            save_json_set(processed_products, PROCESSED_FILE)
            print(f"Processed product: {product_name}")
            time.sleep(1)
    
    print("\nSummary:")
    print(f"Total unique URLs scraped: {len(visited_urls)}")
    print("Content saved with all URLs removed")


# Entry Point
def main():
    csv_file_path = (
        "web_crawling/202601_製品マスタ - translated -  Product Master.csv"
    )
    pdf_extractor = False  
    if not os.path.exists(csv_file_path):
        print(f"CSV file not found: {csv_file_path}")
        return

    process_csv(csv_file_path, pdf_extractor=pdf_extractor)


if __name__ == "__main__":
    main()
