from firecrawl import Firecrawl
from dotenv import load_dotenv
load_dotenv(override=True)

firecrawl = Firecrawl()
def scraping():
    # Batch scrape with markdown format
    job = firecrawl.batch_scrape([
        "https://www.sevensix.co.jp/products/superkfianium_nktp/",
    ], formats=["markdown"], poll_interval=2, timeout=120)

    # Process and save each document
    for doc in job.data:
        markdown = doc.markdown
        
        # Process: remove navigation, clean up content
        # Example: extract only main content sections
        lines = markdown.split('\n')
        processed_lines = [line for line in lines if not line.startswith('[![')]  # remove image links
        processed_content = '\n'.join(processed_lines)
        
        # Save to file
        filename = doc.metadata.source_url.replace('https://', '').replace('/', '_') + '.md'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        print(f"Saved: {filename}")