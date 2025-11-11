import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import trafilatura
import time
from dotenv import load_dotenv
import os
from urllib.robotparser import RobotFileParser


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def crawl_website_content(website_url: str, max_pages: int = 5) -> dict:
    """Crawl a website and extract relevant content with intelligent page discovery"""
    try:
        print(f"🕷️ Starting intelligent web crawl for: {website_url}")
        
        # Validate and normalize URL
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url
        
        # Check robots.txt
        rp = RobotFileParser()
        robots_url = urljoin(website_url, '/robots.txt')
        try:
            rp.set_url(robots_url)
            rp.read()
            if not rp.can_fetch("*", website_url):
                print(f"⚠️ Robots.txt disallows crawling: {website_url}")
                return {"error": "Website disallows crawling via robots.txt"}
        except Exception as e:
            print(f"⚠️ Could not check robots.txt: {e}")
        
        # Headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Get main page
        try:
            response = requests.get(website_url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Error fetching main page: {e}")
            return {"error": f"Could not fetch website: {str(e)}"}
        
        # Parse main page
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract main content using trafilatura
        extracted_text = trafilatura.extract(response.content, include_formatting=True, include_links=True)
        
        if not extracted_text:
            # Fallback to BeautifulSoup if trafilatura fails
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            extracted_text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in extracted_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            extracted_text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Intelligent page discovery
        discovered_urls = set()
        crawled_pages = [website_url]
        additional_content = []
        
        # Discover all links from the main page
        try:
            # Find all links on the main page
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(website_url, href)
                    
                    # Only consider URLs from the same domain
                    if urlparse(absolute_url).netloc == urlparse(website_url).netloc:
                        discovered_urls.add(absolute_url)
            
            # Also look for navigation menus, footers, and other link containers
            link_containers = soup.find_all(['nav', 'menu', 'ul', 'div'], 
                                          class_=lambda x: x and any(word in x.lower() for word in ['nav', 'menu', 'main', 'footer', 'header', 'links']))
            
            for container in link_containers:
                for link in container.find_all('a', href=True):
                    href = link.get('href')
                    if href:
                        absolute_url = urljoin(website_url, href)
                        if urlparse(absolute_url).netloc == urlparse(website_url).netloc:
                            discovered_urls.add(absolute_url)
            
            print(f"🔍 Discovered {len(discovered_urls)} unique URLs from main page")
            
        except Exception as e:
            print(f"⚠️ Error discovering links: {e}")
        
        # Intelligent URL filtering and scoring
        scored_urls = []
        
        for url in discovered_urls:
            score = calculate_url_score(url)
            if score > 0:  # Only include URLs with positive scores
                scored_urls.append((url, score))
        
        # Sort by score (highest first) and take the best ones
        scored_urls.sort(key=lambda x: x[1], reverse=True)
        
        print(f"📊 Found {len(scored_urls)} high-quality URLs to crawl")
        
        # If we don't have enough high-quality URLs, try some fallback strategies
        if len(scored_urls) < max_pages - 1:
            print(f"⚠️ Only found {len(scored_urls)} high-quality URLs, trying fallback discovery...")
            
            # Fallback: Try common paths that might exist
            fallback_paths = [
                '/about', '/about-us', '/company', '/team', '/services', '/products',
                '/contact', '/who-we-are', '/what-we-do', '/mission', '/vision',
                '/blog', '/news', '/resources', '/help', '/support'
            ]
            
            for path in fallback_paths:
                if len(scored_urls) >= max_pages - 1:
                    break
                    
                fallback_url = urljoin(website_url, path)
                if fallback_url not in [url for url, _ in scored_urls]:
                    score = calculate_url_score(fallback_url)
                    if score > 0:
                        scored_urls.append((fallback_url, score))
                        print(f"🔍 Added fallback URL: {fallback_url}")
        
        # Crawl the best URLs
        for url, score in scored_urls[:max_pages - 1]:  # -1 because we already have the main page
            if len(crawled_pages) >= max_pages:
                break
                
            if url not in crawled_pages:
                try:
                    print(f"🕷️ Crawling: {url} (score: {score})")
                    page_response = requests.get(url, headers=headers, timeout=5)
                    if page_response.status_code == 200:
                        page_content = trafilatura.extract(page_response.content, include_formatting=True)
                        if page_content and len(page_content.strip()) > 100:  # Only if substantial content
                            # Extract page title
                            page_soup = BeautifulSoup(page_response.content, 'html.parser')
                            title_tag = page_soup.find('title')
                            page_title = title_tag.get_text().strip() if title_tag else url.split('/')[-1].replace('-', ' ').title()
                            
                            additional_content.append({
                                'url': url,
                                'title': page_title,
                                'content': page_content[:3000]  # Increased content length
                            })
                            crawled_pages.append(url)
                            print(f"✅ Successfully crawled: {page_title}")
                        else:
                            print(f"⚠️ Skipping {url}: insufficient content")
                    time.sleep(1)  # Be respectful
                except Exception as e:
                    print(f"⚠️ Could not crawl {url}: {e}")
        
        # Combine all content
        all_content = f"# {website_url}\n\n{extracted_text}\n\n"
        
        for page in additional_content:
            all_content += f"## {page['title']}\n\n{page['content']}\n\n"
        
        # If we only have the main page, try to extract more sections from it
        if len(crawled_pages) == 1:
            print("📄 Single-page website detected, extracting sections...")
            sections = extract_sections_from_main_page(soup, website_url)
            if sections:
                all_content += "\n## Additional Sections\n\n"
                for section in sections:
                    all_content += f"### {section['title']}\n\n{section['content']}\n\n"
        
        print(f"✅ Successfully crawled {len(crawled_pages)} pages from {website_url}")
        
        return {
            "content": all_content,
            "pages_crawled": len(crawled_pages),
            "urls": crawled_pages,
            "main_url": website_url
        }
        
    except Exception as e:
        print(f"❌ Error crawling website: {e}")
        return {"error": f"Error crawling website: {str(e)}"}
