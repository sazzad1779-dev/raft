from firecrawl import Firecrawl
from dotenv import load_dotenv
import csv
import os
import time

load_dotenv(override=True)

firecrawl = Firecrawl()

def extract_links_from_markdown(markdown):
    """Extract PDF and product links from markdown content"""
    links = []
    
    # Simple regex pattern to find markdown links
    import re
    # Find all markdown links [text](url)
    md_links = re.findall(r'\[.*?\]\((.*?)\)', markdown)
    
    for link in md_links:
        # Check if it's a PDF link
        if link.lower().endswith('.pdf'):
            links.append(('pdf', link))
        # Check if it's a product page (you can customize this pattern)
        # elif '/products/' in link.lower() or '/product/' in link.lower():
        #     links.append(('product', link))
    
    return links

def scrape_url(url, visited_urls):
    """Scrape a single URL and handle embedded links"""
    if url in visited_urls:
        return None
    
    print(f"Scraping: {url}")
    visited_urls.add(url)
    
    try:
        # Scrape the main URL
        job = firecrawl.scrape(
            [url], 
            formats=["markdown"], 
        )
        
        # if not job.data:
        #     print(f"No data returned for {url}")
        #     return None
        
        doc = job.data[0]
        markdown = doc.markdown
        
        # Process: remove navigation, clean up content
        lines = markdown.split('\n')
        processed_lines = []
        
        for line in lines:
            # Skip image links and navigation if needed
            if line.startswith('[![') or 'navigation' in line.lower() or 'menu' in line.lower():
                continue
            processed_lines.append(line)
        
        processed_content = '\n'.join(processed_lines)
        
        # Extract links for PDFs and product pages
        extracted_links = extract_links_from_markdown(processed_content)
        
        # Save main content
        filename = url.replace('https://', '').replace('http://', '').replace('/', '_') + '.md'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        print(f"Saved: {filename}")
        
        return extracted_links
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def scrape_pdf_or_product(url, visited_urls):
    """Handle PDF or product URL scraping"""
    if url in visited_urls:
        return
    
    print(f"Scraping additional resource: {url}")
    visited_urls.add(url)
    
    try:
        job = firecrawl.batch_scrape(
            [url], 
            formats=["markdown"], 
            poll_interval=2, 
            timeout=120
        )
        
        if job.data:
            doc = job.data[0]
            markdown = doc.markdown
            
            # Save with appropriate filename
            if url.lower().endswith('.pdf'):
                filename = url.replace('https://', '').replace('http://', '').replace('/', '_') + '_PDF.md'
            else:
                filename = url.replace('https://', '').replace('http://', '').replace('/', '_') + '_LINKED.md'
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            print(f"Saved additional resource: {filename}")
            
    except Exception as e:
        print(f"Error scraping additional resource {url}: {e}")

def process_csv(csv_file_path):
    """Process URLs from CSV file"""
    visited_urls = set()
    
    # Read CSV file
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            # Get URL from URL column (adjust column name as needed)
            if 'URL' in row:
                url = row['URL'].strip()
            elif 'url' in row:
                url = row['url'].strip()
            else:
                # Try to find any column that might contain URLs
                for key in row:
                    if 'url' in key.lower():
                        url = row[key].strip()
                        break
                else:
                    print(f"No URL found in row: {row}")
                    continue
            
            if not url:
                continue
                
            # Ensure URL has proper scheme
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Scrape main URL
            extracted_links = scrape_url(url, visited_urls)
            
            if extracted_links:
                # Scrape PDFs and product links found
                for link_type, link_url in extracted_links:
                    # Ensure link is absolute
                    if link_url.startswith('/'):
                        # Convert relative URL to absolute
                        from urllib.parse import urljoin
                        link_url = urljoin(url, link_url)
                    
                    scrape_pdf_or_product(link_url, visited_urls)
            
            # Add delay to be polite to the server
            time.sleep(2)
            break
    
    print(f"Total unique URLs scraped: {len(visited_urls)}")

def main():
    # Specify your CSV file path
    csv_file_path = "web_crawling/product.csv"  # Change this to your CSV file path
    
    if not os.path.exists(csv_file_path):
        print(f"CSV file not found: {csv_file_path}")
        print("Please create a CSV file with a 'URL' column containing the URLs to scrape.")
        return
    
    process_csv(csv_file_path)

# if __name__ == "__main__":
#     main()