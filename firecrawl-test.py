from firecrawl.firecrawl import FirecrawlApp
import time
import sys

def main():
    # Initialize Firecrawl with your API key
    api_key = "fc-8931d65d88d84608abe543181f57d7e4"
    app = FirecrawlApp(api_key=api_key)

    # Define the base URL of the documentation
    base_url = "https://docs.firecrawl.dev/"

    try:
        # Using the crawl_url method as shown in documentation
        print("Starting crawl...")
        crawl_response = app.crawl_url(
            base_url,
            {
                'limit': 100, 
                'scrapeOptions': {
                    'formats': ['markdown']
                }
            },
            poll_interval=30
        )

        if not crawl_response.get('success'):
            print("Crawl failed")
            sys.exit(1)

        crawl_data = crawl_response.get('data', [])
        if not crawl_data:
            print("No data found in crawl response")
            sys.exit(1)

        print(f"Successfully crawled {len(crawl_data)} pages")
        
        # Step 2: Extract content from each crawled page
        all_extracted_content = []

        for page in crawl_data:
            # Use the markdown content that's already been crawled
            if isinstance(page, dict):
                markdown_content = page.get('markdown', '')
                metadata = page.get('metadata', {})
                source_url = metadata.get('sourceURL', 'Unknown URL')
                title = metadata.get('title', 'Untitled')

                if markdown_content:
                    formatted_content = f"# {title}\nSource: {source_url}\n\n{markdown_content}\n\n---\n"
                    all_extracted_content.append(formatted_content)
                    print(f"Successfully processed content from {source_url}")
                else:
                    print(f"No markdown content found for {source_url}")
                    # Debug information
                    print(f"Page content structure: {list(page.keys())}")

        # Step 3: Save the extracted content
        if all_extracted_content:
            with open("technical_documentation.md", "w", encoding="utf-8") as f:
                f.write("# Technical Documentation Overview\n\n")
                f.write("Generated with Firecrawl\n\n")
                f.write("\n".join(all_extracted_content))
            
            print("Extraction complete. Documentation saved in 'technical_documentation.md'")
        else:
            print("No content was extracted")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()