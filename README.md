# Flipkart Product Crawler

This script crawls Flipkart product data from a sitemap XML, extracts key product information (title, SKU, description, image), and saves it to a JSON file 
(`Products.json`). It also downloads and resizes product images.

## Features

- Parses Flipkart product sitemap XML or Filters valid product URLs.
- Fetches product pages using rotating proxies and user agents to avoid IP bans and detection
- Extracts product data: title, SKU, description, and image URL.
- Downloads and resizes images to 500x500 pixels.
- Saves the first 50 valid product data entries to `Products.json`.

**Python 3.9+** is recommended. 
## Requirements
Install the necessary packages using `pip`:

```bash
pip install -r requirements.txt
