from firecrawl.firecrawl import FirecrawlApp
import time
import sys
from typing import List, Dict, Optional
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentationCrawler:
    def __init__(self, api_key: str):
        self.app = FirecrawlApp(api_key=api_key)
        
    def crawl_site(self, base_url: str, options: Dict) -> Optional[List[Dict]]:
        """Crawl the website and return the raw crawl data."""
        try:
            start_time = time.time()
            logger.info(f"Starting crawl of {base_url}")
            
            # Use crawl_url_and_watch instead of crawl_url
            watcher = self.app.crawl_url_and_watch(
                base_url,
                options
            )

            crawl_data = []
            current_credits = 0

            # Process pages as they come in
            for update in watcher:
                if update.get('type') == 'crawl.page':
                    page_data = update.get('data', [])
                    if page_data:
                        crawl_data.extend(page_data)
                        credits = update.get('creditsUsed', 0)
                        current_credits += credits
                        logger.info(f"Received page update. Total pages: {len(crawl_data)}, Current credits: {current_credits}")
                elif update.get('type') == 'crawl.completed':
                    logger.info("Crawl completed!")
                elif update.get('type') == 'crawl.failed':
                    error = update.get('error')
                    logger.error(f"Crawl failed: {error}")
                    return None

            elapsed_time = time.time() - start_time    
            logger.info(f"Successfully crawled {len(crawl_data)} pages in {elapsed_time:.2f} seconds")
            return crawl_data
            
        except Exception as e:
            logger.error(f"Crawl failed with error: {str(e)}")
            return None

    def process_page(self, page: Dict) -> Optional[str]:
        """Process a single page and return formatted content."""
        try:
            # For LLM extraction, the content will be in the 'extract' field
            extracted_content = page.get('extract', '')
            metadata = page.get('metadata', {})
            source_url = metadata.get('sourceURL', 'Unknown URL')
            title = metadata.get('title', 'Untitled')

            if not extracted_content:
                logger.warning(f"No extracted content found for {source_url}")
                return None

            formatted_content = f"# {title}\nSource: {source_url}\n\n{extracted_content}\n\n---\n"
            return formatted_content

        except Exception as e:
            logger.error(f"Failed to process page: {str(e)}")
            return None

    def save_documentation(self, content: List[str], output_file: str):
        """Save the processed content to a file."""
        try:
            output_path = Path(output_file)
            with output_path.open("w", encoding="utf-8") as f:
                f.write("# Technical Documentation Overview\n\n")
                f.write("Generated with Firecrawl\n\n")
                f.write("\n".join(content))
            logger.info(f"Documentation saved to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save documentation: {str(e)}")
            return False

    def batch_extract_and_watch(self, urls: List[str], options: Dict) -> Optional[tuple[List[Dict], int]]:
        """Batch extract content with status monitoring."""
        try:
            start_time = time.time()
            max_wait_time = 300  # 5 minutes maximum wait time
            logger.info(f"Starting batch extraction of {len(urls)} URLs")
            
            # Start batch scrape job
            batch_response = self.app.async_batch_scrape_urls(urls, options)
            if not batch_response.get('success'):
                logger.error("Batch extraction failed to start")
                return None
            
            job_id = batch_response.get('id')
            logger.info(f"Batch job started with ID: {job_id}")
            
            # Monitor progress
            last_progress_time = time.time()
            while True:
                status = self.app.check_batch_scrape_status(job_id)
                completed = status.get('completed', 0)
                total = status.get('total', 0)
                
                logger.info(f"Progress: {completed}/{total} pages")
                
                if status.get('status') == 'completed':
                    logger.info("Batch extraction completed!")
                    break
                elif status.get('status') == 'failed':
                    logger.error("Batch extraction failed")
                    return None
                
                # Check if we're stuck (no progress for 2 minutes)
                if completed > 0 and completed == total - 1:  # If we're on the last page
                    if time.time() - last_progress_time > 120:  # 2 minutes without progress
                        logger.warning("Extraction appears stuck on last page, continuing with available results")
                        break
                else:
                    last_progress_time = time.time()
                
                # Check overall timeout
                if time.time() - start_time > max_wait_time:
                    logger.warning("Extraction exceeded maximum wait time, continuing with available results")
                    break
                    
                time.sleep(5)  # Wait before checking again
            
            elapsed_time = time.time() - start_time    
            total_credits = status.get('creditsUsed', 0)
            logger.info(f"Successfully extracted {total} pages in {elapsed_time:.2f} seconds")
            return status.get('data', []), total_credits
            
        except Exception as e:
            logger.error(f"Batch extraction failed with error: {str(e)}")
            return None

def main():
    # Configuration
    API_KEY = "fc-8931d65d88d84608abe543181f57d7e4"
    BASE_URL = "https://docs.firecrawl.dev/"
    OUTPUT_FILE = "technical_documentation-extract.md"
    
    # Initialize crawler
    crawler = DocumentationCrawler(API_KEY)
    
    logger.info("Starting documentation extraction process...")
    
    # Start timing
    total_start_time = time.time()
    
    # First get all URLs from the site
    logger.info(f"Crawling {BASE_URL} for all documentation URLs...")
    crawl_response = crawler.app.crawl_url(
        BASE_URL,
        {
            'limit': 100,  # Adjust if needed
            'scrapeOptions': {
                'formats': ['links']
            }
        }
    )
    
    if not crawl_response.get('success'):
        logger.error("Failed to crawl site for URLs")
        sys.exit(1)
        
    # Extract all URLs
    all_urls = [page['metadata']['sourceURL'] for page in crawl_response.get('data', [])]
    logger.info(f"Found {len(all_urls)} pages to process")
    
    # Configure extraction
    EXTRACT_OPTIONS = {
        'formats': ['extract'],
        'extract': {
            'prompt': """Convert this technical documentation into clear, readable markdown.

                       Key Instructions:
                       1. Transform any JSON/dictionary data into natural language paragraphs
                       2. Keep code examples in proper markdown code blocks
                       3. Preserve important technical details but present them in a readable way
                       4. Use proper markdown headings (##) to organize content
                       5. Convert arrays/lists into proper markdown bullet points
                       
                       For example, instead of:
                       {'title': 'API Docs', 'parameters': [{'name': 'url', 'required': true}]}
                       
                       Write:
                       ## API Documentation
                       
                       This endpoint accepts the following parameters:
                       - url (required): The URL to process
                       
                       Keep the content technical but make it human-readable.""",
        }
    }
    
    # Execute batch extraction with status monitoring
    extraction_result = crawler.batch_extract_and_watch(all_urls, EXTRACT_OPTIONS)
    if not extraction_result:
        sys.exit(1)
        
    extracted_data, total_credits = extraction_result
    
    # Process pages
    processed_content = []
    for page in extracted_data:
        if content := crawler.process_page(page):
            processed_content.append(content)
    
    if not processed_content:
        logger.error("No content was processed")
        sys.exit(1)
    
    # Save documentation
    if not crawler.save_documentation(processed_content, OUTPUT_FILE):
        sys.exit(1)
        
    # Log total time and credits
    total_time = time.time() - total_start_time
    logger.info(f"Total credits used: {total_credits}")
    logger.info(f"Total extraction completed in {total_time:.2f} seconds")

if __name__ == "__main__":
    main()