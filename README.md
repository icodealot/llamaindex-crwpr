## LlamaIndex Custom Readability Web Page Reader

Note, this is a lightly customized version of the same reader found at https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-web/llama_index/readers/web/readability_web

You should use the official reader linked above instead of this one if the original works for your use case. If you are here it is probably because someone sent you here for the same purpose for which I needed this customized version of the reader.


## Usage

This Python module was created fit for a specific purpose and offers the following features beyond the original:

- A customizable `page_sleep` value
- A `load_data` method that accepts a list of URLs
- A callback to receive debug messages from the Chromium browsser used by playwright (useful for debugging)
- Formats text through BeautifulSoup to cleanup oddities

**How-to**:

`crwpr` is designed to be copied into a Python project for use as a locally configured / custom reader. It is not published so you cannot `pip install` it from a centralized repo. The intention is for it to be used as a drop in for projects using LlamaIndex web page readers to overcome some problems I ran into using the reader linked above for my specific use case.

1. Copy the `crwpr/` directory into your project (Read the source!)

2. Make sure the requirements of your project are updated to minimally include those in `crwpr/requirements.txt` (`pip install` them, etc.)

3. This reader relies on Playwright with Chromium so after you `pip install playwright`, install Chromium. For example:

```bash
playwright install chromium
```

3. Import the `CustomReadabilityWebPageReader` in your project and use it.

**Example with Page Sleep loading a single URL**:

```python
from crwpr import CustomReadabilityWebPageReader

url = "https://..."

documents = CustomReadabilityWebPageReader(
    page_sleep=4000,
).load_data(urls=[url])
```

**Example with Debugging Output**:

```python
from crwpr import CustomReadabilityWebPageReader

urls = [ "https://...", ...]

documents = CustomReadabilityWebPageReader(
    debug_callback=lambda msg: print(msg),
).load_data(urls=urls)
```

**Example with multiple options defined**:

```python
from crwpr import CustomReadabilityWebPageReader

urls = [ "https://...", ...]

documents = CustomReadabilityWebPageReader(
    wait_until="domcontentloaded",
    page_sleep=4000,
    debug_callback=lambda msg: print(msg),
).load_data(urls=urls])
```

Note, all other `ReadabilityWebPageReader` parameters apply. View the source in `base.py` if you have any doubts. It is a small file so don't be shy!

**Differences vs. ReadabilityWebPageReader!!!**

There are a few differences in this implementation from the original.

1. This one uses BeautifulSoup to cleanup the text returned.
2. The `load_data` method accepts a list instead of a single URL
3. Internally the use of `asyncio` is slightly different to work with Python 3.14+
