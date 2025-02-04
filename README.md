# WebNovelCrawler

A Python Novel Crawler &amp; Epub Builder using asyncio

This program uses python's new asyncio package to fetch pages.

Works with Python3.5 or higher, but only tested with Python3.6 and Python3.8.10

Syosetu: id means nxxxxxx if you want to crawl ncode.syosetu.com/nxxxxxx/</br></br>
Alphapolis: id means xxxxx/xxxxx if you want to crawl www.alphapolis.co.jp/novel/xxxxx/xxxxx</br></br>
Kakuyomu:id means xxxxxxxx if you want to crawl kakuyomu.jp/works/xxxxxxxx</br></br>

Proxies may or may not be used varies from site to site. Configuration is in the file.

Furigana uses kanome and kakasi to work, and will be slow when processing novel that has a lot of words.

## Example of use
```
> python3 kakuyomu.fixed.py
[Initial] Input novel id here: 1177354054880254749

[Main Thread] Fetching Metadata...
	...
[Coroutine] Fetch Task Finished for Link: https://kakuyomu.jp/works/1177354054880254749/episodes/1177354054882895659
[Main Thread] Building Menu...
[Main Thread] Building Book...
[Main Thread] Finished. File saved.
```

## TODO:
1. More site.
2. Auto proxy swtich to prevent NoneType Error caused by anti-crawl.

## Required libs: 
requests, beautifulsoup4, ebooklib, aiohttp</br>
## Additional required libs for furigana: 
kanome, kakasi
