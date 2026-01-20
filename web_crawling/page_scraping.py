from firecrawl import Firecrawl
from dotenv import load_dotenv
load_dotenv(override=True)

firecrawl = Firecrawl()
def scraping():
    # Batch scrape with markdown format
    doc = firecrawl.scrape(
        "https://www.sevensix.co.jp/products/superkfianium_nktp/",
     formats=["markdown"], only_main_content=False )

    # Process and save each document
    # for doc in job.data:
    markdown = doc.markdown
    print(doc)
    # Process: remove navigation, clean up content
    # Example: extract only main content sections
    lines = markdown.split('\n')
    processed_lines = [line for line in lines if not line.startswith('[![')]  # remove image links
    processed_content = '\n'.join(processed_lines)
    
    # Save to file
    filename = doc.metadata.source_url.replace('https://', '').replace('/', '_') + '2.md'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(processed_content)
    
    print(f"Saved: {filename}")

scraping()