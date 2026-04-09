import asyncio
import unicodedata
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional

from bs4 import BeautifulSoup
from llama_index.core.node_parser.interface import TextSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from playwright.async_api._generated import Browser

path = Path(__file__).parent / "Readability.js"


def nfkc_normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


class CustomReadabilityWebPageReader(BaseReader):
    """
    Custom Readability Webpage Loader.

    Extracting relevant information from a fully rendered web page.
    During the processing, it is always assumed that web pages used as data sources contain textual content.
    Sometimes SPAs do not behave predictably, in those cases it may be useful to set an additional sleep parameter.

    1. Load the page and wait for it rendered. (playwright)
    2. If a custom sleep value is provided, set a JS timeout and wait
    3. Inject Readability.js to extract the main content. (cleans the text with bs4)

    Args:
        proxy (Optional[str], optional): Proxy server. Defaults to None.
        wait_until (Optional[Literal["commit", "domcontentloaded", "load", "networkidle"]], optional): Wait until the page is loaded. Defaults to "domcontentloaded".
        text_splitter (TextSplitter, optional): Text splitter. Defaults to None.
        normalizer (Optional[Callable[[str], str]], optional): Text normalizer. Defaults to nfkc_normalize.
        page_sleep (Optional[int], optional): Arbitrary JS sleep milliseconds before scraping. Defaults to 0.
        debug_callback (Optional[Callable[[str], None]], optional): Debug callback that passes through Chromium console events. Defaults to none.
    """

    def __init__(
        self,
        proxy: Optional[str] = None,
        wait_until: Optional[
            Literal["commit", "domcontentloaded", "load", "networkidle"]
        ] = "domcontentloaded",
        text_splitter: Optional[TextSplitter] = None,
        normalize: Optional[Callable[[str], str]] = nfkc_normalize,
        page_sleep: Optional[int] = 0
        debug_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._launch_options = {
            "headless": True,
        }
        self._wait_until = wait_until
        if proxy:
            self._launch_options["proxy"] = {
                "server": proxy,
            }
        self._text_splitter = text_splitter
        self._normalize = normalize
        self._readability_js = None
        self._page_sleep = page_sleep
        self._debug_callback = debug_callback


    async def async_load_data(self, url: str) -> List[Document]:
        """
        Render and load data content from url.

        Args:
            url (str): URL to scrape.

        Returns:
            List[Document]: List of documents.

        """
        from playwright.async_api import async_playwright

        async with async_playwright() as async_playwright:
            browser = await async_playwright.chromium.launch(**self._launch_options)

            article = await self.scrape_page(
                browser,
                url,
            )

            if article is None:
                raise ValueError(f"unable to read content from {url}")
                return []
            
            extra_info = {
                key: article[key]
                for key in [
                    "title",
                    "length",
                    "excerpt",
                    "byline",
                    "dir",
                    "lang",
                    "siteName",
                ]
            }

            extra_info["url"] = url

            if self._normalize is not None:
                article["textContent"] = self._normalize(article["textContent"])
            texts = []
            if self._text_splitter is not None:
                texts = self._text_splitter.split_text(article["textContent"])
            else:
                texts = [article["textContent"]]

            await browser.close()

            return [Document(text=x, extra_info=extra_info) for x in texts]


    def load_data(self, urls: List[str]) -> List[Document]:
        """
        Creates a LlamaIndex Document from the contents of each url.
        
        Args:
            urls (List[str]): A list of URLs to scrape.

        Returns:
            Documents: a list of Document objects
        """
        documents = []
        for url in urls:
            documents.extend(asyncio.run(self.async_load_data(url)))
        return documents


    async def scrape_page(
        self,
        browser: Browser,
        url: str,
    ) -> Dict[str, str]:
        """
        Scrape a single article url.

        Args:
            browser (Any): a Playwright Chromium browser.
            url (str): URL of the article to scrape.

        Returns:
            Ref: https://github.com/mozilla/readability
            title: article title;
            content: HTML string of processed article content;
            textContent: text content of the article, with all the HTML tags removed;
            length: length of an article, in characters;
            excerpt: article description, or short excerpt from the content;
            byline: author metadata;
            dir: content direction;
            siteName: name of the site.
            lang: content language

        """
        if self._readability_js is None:
            with open(path) as f:
                self._readability_js = f.read()

        page = await browser.new_page(ignore_https_errors=True)
        page.set_default_timeout(60000)
        if self._debug_callback is not None:
            page.on("console", lambda msg: self._debug_callback(f"[{msg.type}] {msg.text}"))

        await page.goto(url, wait_until=self._wait_until)

        if self._page_sleep > 0:
            await page.evaluate(f"() => new Promise(resolve => setTimeout(resolve, {self._page_sleep}))")

        r = await page.evaluate(f"""
            (function(){{
            {self._readability_js}
            function executor() {{
                return new Readability(document).parse();
            }}
            return executor();
            }}())
        """)

        await page.close()

        r["textContent"] = BeautifulSoup(r["content"], "html.parser").get_text(separator=" ", strip=True)

        print("scraped:", url)

        return r