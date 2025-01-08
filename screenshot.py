import os
import time
import random
import base64
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from Wappalyzer import Wappalyzer, WebPage
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from urllib.parse import urlparse
import urllib3
import warnings
from termcolor import colored
from webdriver_manager.chrome import ChromeDriverManager
import json
import aiohttp
import asyncio

# Suppress Wappalyzer UserWarnings
warnings.filterwarnings("ignore", category=UserWarning, module="Wappalyzer.*")

# Disable InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Start measuring time
start_time = time.time()

# Add a random delay between 1 to 5 seconds before each request
time.sleep(random.uniform(1, 5))

# Define the main output directory
output_dir = "output"

# Function to validate URLs
def validate_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ["http", "https"] and parsed.netloc

# Load user-agents from the specified file
def load_user_agents(file_path):
    with open(file_path, 'r') as f:
        user_agents = [line.strip() for line in f if line.strip()]
    return user_agents

# Rotate user-agents for each request
def get_random_user_agent(user_agents):
    return random.choice(user_agents)

# Define the path to your user-agents file
user_agents_file = "/Users/shashankbhure/my_tools/dirsearch/db/user-agents.txt"
user_agents = load_user_agents(user_agents_file)

# Asynchronous function to fetch URL details
async def fetch_url(session, url, headers):
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            html = await response.text()
            return {
                "url": url,
                "status_code": response.status,
                "headers": dict(response.headers),
                "html": html
            }
    except Exception as e:
        return {"url": url, "error": str(e)}

# Asynchronous function to fetch all URLs
async def fetch_all_urls(urls, headers):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url, headers) for url in urls if validate_url(url)]
        return await asyncio.gather(*tasks)

# Function to make a request with a random user-agent
def make_request_with_random_user_agent(url):
    user_agent = get_random_user_agent(user_agents)
    headers = {
        'User-Agent': user_agent
    }

    try:
        # Add a random delay between 1 to 5 seconds before each request
        time.sleep(random.uniform(1, 5))

        # Make the request with the selected user-agent
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        print(f"Processed {url} with status code: {response.status_code} using User-Agent: {user_agent}")

        return response

    except requests.exceptions.RequestException as e:
        print(f"Failed to process {url}: {e}")
        return None

def create_directories(domain):
    domain_dir = os.path.join(output_dir, domain)
    screenshots_dir = os.path.join(domain_dir, "screenshots")
    headers_dir = os.path.join(domain_dir, "headers")
    html_dir = os.path.join(domain_dir, "html")
    json_dir = os.path.join(domain_dir, "json")

    os.makedirs(screenshots_dir, exist_ok=True)
    os.makedirs(headers_dir, exist_ok=True)
    os.makedirs(html_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    return screenshots_dir, headers_dir, html_dir, json_dir

def process_website(url, screenshots_dir, headers_dir):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    chrome_service = Service("/opt/homebrew/bin/chromedriver")
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        browser.get(url)
        screenshot_path = os.path.join(screenshots_dir, f"{url.split('//')[-1].replace('/', '_')}.png")
        browser.save_screenshot(screenshot_path)

        response = requests.get(url, timeout=5, verify=False)
        headers = response.headers

        headers_path = os.path.join(headers_dir, f"{url.split('//')[-1].replace('/', '_')}_headers.txt")
        with open(headers_path, "w") as f:
            for header, value in headers.items():
                f.write(f"{header}: {value}\n")

        webpage = WebPage.new_from_url(url)
        wappalyzer = Wappalyzer.latest()

        try:
            services = wappalyzer.analyze(webpage)
        except Exception as e:
            print(f"Error analyzing {url} with Wappalyzer: {e}")
            services = []

        services_info = [f"{service['name']} - {service.get('version', 'N/A')}" if isinstance(service, dict) else service for service in services]
        services_summary = "\n".join(services_info) if services_info else "No services detected."

        return screenshot_path, headers, services_summary, response.status_code

    except Exception as e:
        print(f"Failed to process {url}: {e}")
        return None, None, None, None

    finally:
        browser.quit()

# Save raw JSON results
def save_json_results(results, json_dir):
    json_path = os.path.join(json_dir, "results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print(f"Saved JSON results to {json_path}")

# Generate HTML report
def generate_html_report(screenshots, html_dir):
    html_content = '''
    <html>
    <head>
        <title>Website Screenshots with Headers and Services</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

            body {
                margin: 0;
                padding: 0;
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
                background-size: 200% 200%;
                animation: gradientShift 15s ease infinite;
                color: #333;
                text-align: center;
            }

            @keyframes gradientShift {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            h1 {
                font-size: 2.8em;
                margin-top: 50px;
                color: #333;
                font-weight: 600;
            }

            .screenshot-container {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 40px;
                padding: 50px;
                max-width: 1400px;
                margin: 0 auto;
            }

            .screenshot {
                width: 300px;
                background: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(10px);
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
                text-align: center;
                overflow: hidden;
                position: relative;
            }

            .screenshot:hover {
                transform: translateY(-10px);
                box-shadow: 0 30px 50px rgba(0, 0, 0, 0.2);
            }

            img {
                max-width: 100%;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            img:hover {
                opacity: 0.9;
            }

            a {
                text-decoration: none;
                color: #007aff;
                font-weight: 600;
                margin-top: 15px;
                display: block;
            }

            a:hover {
                text-decoration: underline;
            }

            .headers, .services {
                margin-top: 20px;
                background-color: rgba(240, 240, 240, 0.9);
                padding: 15px;
                border-radius: 10px;
                text-align: left;
                color: #333;
                font-size: 0.9em;
                max-height: 150px;
                overflow-y: auto;
                box-shadow: 0 5px 10px rgba(0, 0, 0, 0.05);
            }

            pre {
                white-space: pre-wrap;
                word-wrap: break-word;
                color: #555;
            }

            /* Modal styles */
            .modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.7);
                justify-content: center;
                align-items: center;
            }

            .modal-content {
                margin: auto;
                display: block;
                max-width: 80%;
                max-height: 80%;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }

            .close {
                position: absolute;
                top: 20px;
                right: 40px;
                color: white;
                font-size: 40px;
                font-weight: bold;
                cursor: pointer;
            }
        </style>
    <div id="myModal" class="modal">
        <span class="close" onclick="closeModal()">&times;</span>
        <img class="modal-content" id="modalImage" alt="Expanded View">
    </div>

    <script>
        function openModal(imageSrc) {
            const modal = document.getElementById("myModal");
            const img = document.getElementById("modalImage");
            img.src = imageSrc;
            modal.style.display = "flex";
        }

        function closeModal() {
            const modal = document.getElementById("myModal");
            modal.style.display = "none";
        }

        // Close modal when clicking outside the image
        window.onclick = function(event) {
            const modal = document.getElementById("myModal");
            if (event.target === modal) {
                closeModal();
            }
        };
    </script>
    </head>
    <body>
        <h1>Website Screenshots with Headers and Services</h1>
        <div class="screenshot-container">
    '''

    for url, screenshot, headers, services in screenshots:
        html_content += f'''
        <div class="screenshot">
            <img src="{screenshot}" alt="Screenshot of {url}" onclick="openModal('{screenshot}')">
            <a href="{url}" target="_blank">{url}</a>
            <div class="headers">
                <h3>HTTP Headers</h3>
                <pre>{headers}</pre>
            </div>
            <div class="services">
                <h3>Detected Services</h3>
                <pre>{services}</pre>
            </div>
        </div>
        '''

    html_content += '''
        </div>
    </body>
    </html>
    '''

    # Save HTML report
    html_file_path = os.path.join(html_dir, "report.html")
    with open(html_file_path, "w") as html_file:
        html_file.write(html_content)

    print(f"HTML report generated: {html_file_path}")

# Main execution with multi-threading
def main():
    screenshots = []
    status_counts = defaultdict(int)

    filename = input("Enter the filename (including .txt) that contains the URLs: ")
    with open(filename, "r") as file:
        urls = [line.strip() for line in file if line.strip()]

    if urls:
        main_domain = urls[0].split('//')[-1].split('/')[0]
        screenshots_dir, headers_dir, html_dir, json_dir = create_directories(main_domain)

        headers = {"User-Agent": "Mozilla/5.0 (Website Analyzer Tool)"}

        # Fetch URL data asynchronously
        async_results = asyncio.run(fetch_all_urls(urls, headers))

        # Save raw JSON results
        save_json_results(async_results, json_dir)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_website, url, screenshots_dir, headers_dir): url for url in urls}

            successful_requests = 0
            failed_requests = 0

            for future in as_completed(futures):
                url = futures[future]
                try:
                    screenshot_path, headers, services, status_code = future.result()
                    if screenshot_path and headers:
                        successful_requests += 1
                        status_counts[f"{status_code // 100}xx"] += 1

                        # Color the status code output based on its range
                        if 200 <= status_code < 300:
                            status_message = colored(f"{status_code} OK", "green")
                        elif 300 <= status_code < 400:
                            status_message = colored(f"{status_code} Redirection", "yellow")
                        elif 400 <= status_code < 500:
                            status_message = colored(f"{status_code} Client Error", "red")
                        elif 500 <= status_code < 600:
                            status_message = colored(f"{status_code} Server Error", "magenta")
                        else:
                            status_message = colored(f"{status_code} Unknown", "white")

                        print(f"Processed {url} with status code: {status_message}")
                        with open(screenshot_path, "rb") as img_file:
                            encoded_image = base64.b64encode(img_file.read()).decode('utf-8')
                            screenshots.append((url, f"data:image/png;base64,{encoded_image}", headers, services))
                    else:
                        failed_requests += 1
                except Exception as e:
                    failed_requests += 1

        generate_html_report(screenshots, html_dir)

def print_summary(total_urls, successful_requests, failed_requests, status_counts):
    print("\nSummary of Requests:")
    print(f"Targets: {total_urls}")
    print(f"Threads: 10")
    print(f"- Successful: {successful_requests}")
    print(f"- Failed: {failed_requests}")
    for status_group in ["2xx", "3xx", "4xx", "5xx"]:
        print(f"- {status_group}: {status_counts[status_group]}")
    print(f"\nWrote HTML report to: {os.path.join('output', 'report.html')}")

    elapsed_time = time.time() - start_time
    print(f"Total execution time: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()