# coding:utf-8
# python test.py https://www.aozora.gr.jp/cards/000051/files/47086_27953.html --title "淡島寒月氏" --author "幸田露伴" --card_id 000051 --file_id 47086_27953 --description "A great novel"

import argparse
import requests
from bs4 import BeautifulSoup
import os
from ebooklib import epub
import sys
import linecache
import re

# Configuration
dirn = os.getcwd()
hd = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0'
}
requests.packages.urllib3.disable_warnings()

# CSS for EPUB formatting
css = '''@namespace h "http://www.w3.org/1999/xhtml";
body {
  display: block;
  margin: 5pt;
  page-break-before: always;
  text-align: justify;
}
h1, h2, h3, h4 {
  font-weight: bold;
  margin-bottom: 1em;
  margin-left: 0;
  margin-right: 0;
  margin-top: 1em;
}
p {
  margin-bottom: 1em;
  margin-left: 0;
  margin-right: 0;
  margin-top: 1em;
}
a {
  color: inherit;
  text-decoration: inherit;
  cursor: default;
}
a[href] {
  color: blue;
  text-decoration: none;
  cursor: pointer;
}
a[href]:hover {
  color: red;
}
.center {
  text-align: center;
}
.cover {
  height: 100%;
}'''

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))

def get_page(url):
    try:
        response = requests.get(url, headers=hd, verify=False)
        response.raise_for_status()
        # Aozora Bunko uses Shift_JIS encoding
        encoding = response.encoding if response.encoding != 'ISO-8859-1' else 'shift-jis'
        response.encoding = encoding if encoding else 'shift-jis'
        return response
    except Exception as e:
        PrintException()
        sys.exit(1)

def clean_content(content):
    """Clean HTML content by removing ruby annotations, gaiji images, and invalid XML characters."""
    # Remove ruby annotations
    content = re.sub(r'<ruby><rb>([^<]+)</rb><rp>\(</rp><rt>[^<]+</rt><rp>\)</rp></ruby>', r'\1', content)
    # Remove gaiji image tags
    content = re.sub(r'<img src="[^"]+" alt="[^"]+" class="gaiji" />', '', content)
    # Remove invalid XML characters
    content = re.sub(r'[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]', '', content)
    # Parse and clean HTML structure
    soup = BeautifulSoup(content, 'lxml')
    for tag in soup.find_all(['p', 'div']):
        tag.attrs = {}  # Remove inline styles to rely on CSS
    return str(soup)

def build_page(content, title, chapter_id):
    # Clean the content before building the page
    cleaned_content = clean_content(content)
    html = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ja">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="style/nav.css"/>
</head>
<body>
    <div>
        <h3>{title}</h3>
        {cleaned_content}
    </div>
</body>
</html>'''
    filename = f'chapter_{chapter_id}.xhtml'
    epub_page = epub.EpubHtml(title=title, file_name=filename, content=html.encode('utf-8'), lang='ja')
    return filename, epub_page

class AozoraNovel:
    def __init__(self, url, card_id, file_id, title, author, description):
        self.url = url
        self.card_id = card_id
        self.file_id = file_id
        self.book = epub.EpubBook()
        self.book.set_identifier(f'aozora_{card_id}_{file_id}')
        self.book.set_language('ja')
        self.book.spine = []
        self.chapters = []
        self.novel_title = title.strip()
        self.author = author.strip()
        self.about = description.strip() if description else 'No description provided.'

    def get_meta(self):
        print('[Main Thread] Setting Metadata from command-line arguments...')
        if not self.novel_title or not self.author:
            print("Error: Title and author must not be empty.")
            sys.exit(1)
        self.book.set_title(self.novel_title)
        self.book.add_author(self.author)
        # Sanitize description to avoid invalid XML characters
        self.book.add_metadata('DC', 'description', re.sub(r'[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]', '', self.about))

    def get_content(self):
        print('[Main Thread] Fetching Content...')
        content_page = get_page(self.url)
        soup = BeautifulSoup(content_page.content, 'lxml', from_encoding=content_page.encoding)
        
        # Verify metadata
        meta_title = soup.find('meta', attrs={'name': 'DC.Title'})
        meta_author = soup.find('meta', attrs={'name': 'DC.Creator'})
        if meta_title and meta_author:
            if meta_title['content'] != self.novel_title or meta_author['content'] != self.author:
                print("Warning: Provided title or author does not match metadata.")
        
        # Extract main content
        main_content = soup.select_one('div.main_text')
        if not main_content:
            print("Warning: No main content found. Adding default chapter.")
            default_content = '<p>No content was found for this novel. This is a placeholder chapter.</p>'
            chapters = [(self.novel_title, default_content)]
        else:
            # Treat the entire main_text as one chapter
            chapters = [(self.novel_title, main_content.decode_contents())]
        
        # Build EPUB pages
        self.chapters = []  # Reset chapters list
        for i, (title, content) in enumerate(chapters, 1):
            filename, epub_page = build_page(content, title, i)
            self.chapters.append((filename, title, epub_page))
            self.book.add_item(epub_page)
        print(f'[Debug] Chapters created: {len(self.chapters)}')

    def build_menu(self):
        print('[Main Thread] Building Menu...')
        if not self.chapters:
            print("Error: No chapters to include in TOC. Aborting.")
            sys.exit(1)
        toc_items = []
        for filename, title, epub_page in self.chapters:
            toc_items.append(epub.Link(filename, title, filename))
        self.book.toc = toc_items  # Simplified TOC without Section
        print(f'[Debug] TOC items: {len(toc_items)}')

    def post_process(self):
        print('[Main Thread] Adding NCX and Nav...')
        # Add NCX file
        ncx_item = epub.EpubNcx()
        self.book.add_item(ncx_item)
        
        # Create minimal EpubNav item
        nav_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">
<head>
    <title>Navigation</title>
    <link rel="stylesheet" type="text/css" href="style/nav.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
'''
        for filename, title, _ in self.chapters:
            nav_content += f'            <li><a href="{filename}">{title}</a></li>\n'
        nav_content += '''        </ol>
    </nav>
</body>
</html>'''
        nav_item = epub.EpubNav(uid="nav", file_name="nav.xhtml")
        nav_item.content = nav_content.encode('utf-8')
        self.book.add_item(nav_item)
        
        # Add CSS file
        css_item = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=css.encode('utf-8'))
        self.book.add_item(css_item)
        
        # Set spine
        self.book.spine = ['nav'] + [chapter[2] for chapter in self.chapters]
        print(f'[Debug] Spine: {self.book.spine}')
        print(f'[Debug] Items: {[item.file_name for item in self.book.items]}')

    def build_epub(self):
        print('[Main Thread] Building Book...')
        if not self.chapters:
            print("Error: No chapters to build EPUB. Aborting.")
            sys.exit(1)
        safe_title = re.sub(r'[^\w\s-]', '', self.novel_title)[:63]
        safe_title = safe_title.replace(' ', '_').strip() or 'novel'
        file_name = f'{safe_title}.epub'
        try:
            # Validate EPUB structure
            if not self.book.toc or not self.book.spine or not self.book.items:
                print("Error: TOC, spine, or items list is not properly configured.")
                sys.exit(1)
            print(f'[Debug] Writing EPUB with {len(self.book.items)} items')
            epub.write_epub(os.path.join(dirn, file_name), self.book, {})
            print(f'[Main Thread] Finished. File saved as {file_name}')
        except Exception as e:
            PrintException()
            print("Error during EPUB writing. Checking generated file...")
            if os.path.exists(os.path.join(dirn, file_name)):
                print("EPUB file was generated despite the error.")
                # Attempt to validate EPUB
                try:
                    from epubcheck import EpubCheck
                    result = EpubCheck(os.path.join(dirn, file_name))
                    if result.valid:
                        print("Generated EPUB is valid.")
                    else:
                        print("Generated EPUB has validation errors:", result.messages)
                except ImportError:
                    print("EPUB validation skipped: 'epubcheck' library not installed.")
            else:
                print("EPUB file was not generated.")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Convert Aozora Bunko novel to EPUB.')
    parser.add_argument('url', help='Aozora Bunko URL (e.g., https://www.aozora.gr.jp/cards/000051/files/47086_27953.html)')
    parser.add_argument('--title', required=True, help='Title of the novel')
    parser.add_argument('--author', required=True, help='Author of the novel')
    parser.add_argument('--card_id', required=True, help='Card ID of the novel')
    parser.add_argument('--file_id', required=True, help='File ID of the novel')
    parser.add_argument('--description', default='', help='Description of the novel (optional)')
    
    args = parser.parse_args()
    
    novel = AozoraNovel(args.url, args.card_id, args.file_id, args.title, args.author, args.description)
    novel.get_meta()
    novel.get_content()
    novel.build_menu()
    novel.post_process()
    novel.build_epub()

if __name__ == '__main__':
    main()