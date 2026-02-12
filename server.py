"""
📚 阅读计划协作管理工具 - Python 服务器
使用 Python 标准库，无需安装任何额外依赖。

启动方式: python server.py
访问地址: http://localhost:3000
"""

import http.server
import json
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
import socketserver
import urllib.request
import urllib.error
import urllib.parse
import concurrent.futures
import re
import html as html_lib

SEARCH_USER_AGENT = 'ReadingClubApp/1.0 (+https://openlibrary.org)'
DOUBAN_CACHE = {}

PORT = int(os.environ.get('PORT', 3000))
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'books.json')
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')


def normalize_text(value):
    text = str(value or '').strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def normalize_key(title, author):
    raw = f"{normalize_text(title)}|{normalize_text(author)}"
    return re.sub(r'[^\w\u4e00-\u9fff]+', '', raw)


def to_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def score_match(query_title, query_author, candidate_title, candidate_author):
    title_q = normalize_text(query_title)
    author_q = normalize_text(query_author)
    title_c = normalize_text(candidate_title)
    author_c = normalize_text(candidate_author)

    score = 0
    if title_q:
        if title_c == title_q:
            score += 85
        elif title_c.startswith(title_q):
            score += 55
        elif title_q in title_c:
            score += 35

    if author_q:
        if author_c == author_q:
            score += 35
        elif author_c.startswith(author_q):
            score += 22
        elif author_q in author_c:
            score += 15

    return score


def merge_resources(resources):
    def normalize_url(url):
        fixed = str(url or '').strip()
        if fixed.startswith('http://books.google.com'):
            fixed = fixed.replace('http://', 'https://', 1)
        if fixed.startswith('http://play.google.com'):
            fixed = fixed.replace('http://', 'https://', 1)
        if fixed.startswith('http://archive.org'):
            fixed = fixed.replace('http://', 'https://', 1)
        return fixed

    merged = []
    seen = set()
    for item in resources or []:
        url = normalize_url(item.get('url', ''))
        if not url or url in seen:
            continue
        seen.add(url)
        merged.append({
            'name': item.get('name', '资源链接'),
            'url': url,
            'type': item.get('type', '详情')
        })
    return merged[:8]


def append_discovery_resources(resources, title, author):
    query = urllib.parse.quote(f"{title} {author}".strip())
    out = list(resources or [])

    # 统一判定是否已经有可直接阅读/借阅的资源
    has_readable = any((r.get('type') in ('电子书', '在线阅读', '借阅')) for r in out)
    if has_readable:
        return merge_resources(out)

    # 兜底：合法平台检索入口，避免“完全找不到”
    out.extend([
        {
            'name': '豆瓣读书检索',
            'url': f'https://m.douban.com/search/?query={query}&type=book',
            'type': '检索'
        },
        {
            'name': '微信读书检索',
            'url': f'https://weread.qq.com/web/search/books?keyword={query}',
            'type': '检索'
        },
        {
            'name': 'Google Play Books 检索',
            'url': f'https://play.google.com/store/search?q={query}&c=books',
            'type': '检索'
        }
    ])

    return merge_resources(out)


def has_real_synopsis(text):
    content = str(text or '').strip()
    if not content:
        return False
    return not content.startswith('暂无可公开抓取的详细简介')


def contains_cjk(text):
    value = str(text or '')
    return bool(re.search(r'[\u4e00-\u9fff]', value))


def clean_html_text(raw_html):
    text = re.sub(r'<br\s*/?>', '\n', raw_html, flags=re.I)
    text = re.sub(r'</p\s*>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = html_lib.unescape(text)
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    text = re.sub(r'\n+', '\n', text).strip()
    return text


def fetch_douban_best_metadata(title, author=''):
    cache_key = normalize_key(title, author)
    if cache_key in DOUBAN_CACHE:
        return DOUBAN_CACHE[cache_key]

    try:
        query = urllib.parse.quote(f"{title} {author}".strip())
        search_url = f"https://m.douban.com/search/?query={query}&type=book"
        req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        search_html = urllib.request.urlopen(req, timeout=8).read().decode('utf-8', 'ignore')

        subject_ids = re.findall(r'href="/book/subject/(\d+)/"', search_html)
        unique_ids = []
        for sid in subject_ids:
            if sid not in unique_ids:
                unique_ids.append(sid)
        unique_ids = unique_ids[:5]

        best = None
        best_score = -1

        for sid in unique_ids:
            detail_url = f"https://book.douban.com/subject/{sid}/"
            dreq = urllib.request.Request(detail_url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(dreq, timeout=8).read().decode('utf-8', 'ignore')

            title_match = re.search(r'<span\s+property="v:itemreviewed">([^<]+)</span>', html)
            db_title = html_lib.unescape(title_match.group(1).strip()) if title_match else ''

            info_match = re.search(r'<div\s+id="info"[^>]*>([\s\S]*?)</div>', html)
            info_text = clean_html_text(info_match.group(1)) if info_match else ''
            author_match = re.search(r'作者[:：]\s*([^\n/]+)', info_text)
            db_author = author_match.group(1).strip() if author_match else ''

            score = score_match(title, author, db_title, db_author)

            rating_match = re.search(r'<strong\s+class="ll rating_num\s*"[^>]*>\s*([0-9.]+)\s*</strong>', html)
            db_rating = to_float(rating_match.group(1)) if rating_match else None
            if db_rating:
                score += 6

            intros = re.findall(r'<div\s+class="intro">([\s\S]*?)</div>', html)
            intro_texts = [clean_html_text(x) for x in intros if clean_html_text(x)]
            intro = max(intro_texts, key=len) if intro_texts else ''
            if intro:
                score += 8

            candidate = {
                'title': db_title,
                'author': db_author,
                'synopsis': intro[:420],
                'rating': round(db_rating, 1) if db_rating else None,
                'ratingSource': '豆瓣' if db_rating else '',
                'source': '豆瓣',
                'resource': {
                    'name': '豆瓣页面',
                    'url': detail_url,
                    'type': '详情'
                }
            }

            if score > best_score:
                best_score = score
                best = candidate

        # 低匹配结果直接忽略，避免误填
        if best_score < 30:
            DOUBAN_CACHE[cache_key] = None
            return None

        DOUBAN_CACHE[cache_key] = best
        return best
    except Exception:
        DOUBAN_CACHE[cache_key] = None
        return None


def build_openlibrary_resources(doc):
    resources = []
    title = doc.get('title', '')
    author = ', '.join(doc.get('author_name', [])[:1]) if doc.get('author_name') else ''
    query = urllib.parse.quote(f"{title} {author}".strip())

    if doc.get('key'):
        resources.append({
            'name': 'Open Library 页面',
            'url': f"https://openlibrary.org{doc['key']}",
            'type': '详情'
        })

    ia_ids = doc.get('ia', []) or []
    if ia_ids:
        resources.append({
            'name': 'Internet Archive 借阅/预览',
            'url': f"https://archive.org/details/{ia_ids[0]}",
            'type': '借阅'
        })

    if doc.get('ebook_access') in ('public', 'borrowable', 'printdisabled') and doc.get('key'):
        resources.append({
            'name': 'Open Library 电子版入口',
            'url': f"https://openlibrary.org{doc.get('key', '')}",
            'type': '电子书'
        })

    resources.append({
        'name': 'Google Books 检索',
        'url': f'https://books.google.com/books?q={query}',
        'type': '检索'
    })
    return merge_resources(resources)


def build_google_resources(item):
    volume = item.get('volumeInfo', {})
    access = item.get('accessInfo', {})
    resources = []

    if volume.get('infoLink'):
        resources.append({'name': 'Google Books 页面', 'url': volume['infoLink'], 'type': '详情'})
    if volume.get('previewLink'):
        resources.append({'name': 'Google Books 预览', 'url': volume['previewLink'], 'type': '预览'})
    if access.get('webReaderLink'):
        resources.append({'name': 'Google Web Reader', 'url': access['webReaderLink'], 'type': '在线阅读'})

    epub = (access.get('epub') or {})
    pdf = (access.get('pdf') or {})
    if epub.get('isAvailable') and epub.get('acsTokenLink'):
        resources.append({'name': 'Google EPUB 获取', 'url': epub['acsTokenLink'], 'type': '电子书'})
    if pdf.get('isAvailable') and pdf.get('acsTokenLink'):
        resources.append({'name': 'Google PDF 获取', 'url': pdf['acsTokenLink'], 'type': '电子书'})

    return merge_resources(resources)


def build_gutendex_resources(book):
    formats = book.get('formats', {}) or {}
    resources = []

    for fmt_key, fmt_url in formats.items():
        if not fmt_url or fmt_url.endswith('.zip'):
            continue
        if 'text/html' in fmt_key:
            resources.append({'name': 'Project Gutenberg 在线阅读', 'url': fmt_url, 'type': '在线阅读'})
        elif 'application/epub+zip' in fmt_key:
            resources.append({'name': 'Project Gutenberg EPUB', 'url': fmt_url, 'type': '电子书'})
        elif 'application/pdf' in fmt_key:
            resources.append({'name': 'Project Gutenberg PDF', 'url': fmt_url, 'type': '电子书'})

    if book.get('id'):
        resources.append({
            'name': 'Gutendex 详情',
            'url': f"https://gutendex.com/books/{book['id']}",
            'type': '详情'
        })

    return merge_resources(resources)


def fetch_openlibrary_candidates(title, author=''):
    fields = ','.join([
        'key', 'title', 'author_name', 'first_publish_year', 'cover_i',
        'ratings_average', 'ratings_count', 'subject', 'ia', 'ebook_access'
    ])
    url = f"https://openlibrary.org/search.json?title={urllib.parse.quote(title)}&limit=12&fields={fields}"
    if author:
        url += f"&author={urllib.parse.quote(author)}"

    data = fetch_json(url, timeout=7)
    results = []
    for doc in data.get('docs', []):
        book_title = doc.get('title', '')
        book_author = ', '.join(doc.get('author_name', [])[:2]) if doc.get('author_name') else ''

        rating = to_float(doc.get('ratings_average'))
        rating_count = int(doc.get('ratings_count', 0) or 0)
        score = score_match(title, author, book_title, book_author)
        if rating:
            score += 8
        if rating_count:
            score += min(12, rating_count // 40)
        if doc.get('cover_i'):
            score += 5
        if doc.get('first_publish_year'):
            score += 2

        cover = ''
        if doc.get('cover_i'):
            cover = f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-M.jpg"

        results.append({
            'title': book_title,
            'author': book_author,
            'synopsis': '',
            'rating': round(rating, 1) if rating else None,
            'ratingSource': 'Open Library' if rating else '',
            'category': map_category(doc.get('subject', [])[:5]),
            'cover': cover,
            'year': doc.get('first_publish_year'),
            'source': 'Open Library',
            'resources': build_openlibrary_resources(doc),
            '_score': score,
            '_work_key': doc.get('key', '')
        })
    return results


def fetch_googlebooks_candidates(title, author=''):
    query_parts = [f"intitle:{title}"]
    if author:
        query_parts.append(f"inauthor:{author}")
    query = urllib.parse.quote(' '.join(query_parts))
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=12&printType=books"

    data = fetch_json(url, timeout=7)
    items = data.get('items', [])
    results = []

    for item in items:
        volume = item.get('volumeInfo', {})
        book_title = volume.get('title', '')
        book_author = ', '.join(volume.get('authors', [])[:2]) if volume.get('authors') else ''
        rating = to_float(volume.get('averageRating'))
        ratings_count = int(volume.get('ratingsCount', 0) or 0)

        score = score_match(title, author, book_title, book_author)
        if rating:
            score += 7
        if ratings_count:
            score += min(10, ratings_count // 50)
        if volume.get('description'):
            score += 4
        if volume.get('imageLinks', {}).get('thumbnail'):
            score += 3

        image_links = volume.get('imageLinks', {}) or {}
        cover = image_links.get('thumbnail', '') or image_links.get('smallThumbnail', '')
        if cover.startswith('http://'):
            cover = cover.replace('http://', 'https://', 1)

        year = None
        published_date = str(volume.get('publishedDate', ''))
        if published_date[:4].isdigit():
            year = int(published_date[:4])

        categories = volume.get('categories', [])[:3]
        description = str(volume.get('description', '')).strip()[:260]

        results.append({
            'title': book_title,
            'author': book_author,
            'synopsis': description,
            'rating': round(rating, 1) if rating else None,
            'ratingSource': 'Google Books' if rating else '',
            'category': map_category(categories),
            'cover': cover,
            'year': year,
            'source': 'Google Books',
            'resources': build_google_resources(item),
            '_score': score,
            '_work_key': ''
        })

    return results


def fetch_gutendex_candidates(title, author=''):
    query = urllib.parse.quote(f"{title} {author}".strip())
    url = f"https://gutendex.com/books?search={query}"

    data = fetch_json(url, timeout=7)
    results = []
    for book in (data.get('results', []) or [])[:12]:
        book_title = book.get('title', '')
        book_author = ', '.join([a.get('name', '') for a in (book.get('authors') or []) if a.get('name')][:2])
        score = score_match(title, author, book_title, book_author)
        if book.get('download_count'):
            score += min(8, int(book.get('download_count', 0)) // 200)

        subjects = [s for s in (book.get('subjects') or [])[:4]]
        synopsis = ''
        if subjects:
            synopsis = f"主题: {' / '.join(subjects[:3])}"

        results.append({
            'title': book_title,
            'author': book_author,
            'synopsis': synopsis,
            'rating': None,
            'ratingSource': '',
            'category': map_category(subjects),
            'cover': '',
            'year': None,
            'source': 'Gutendex',
            'resources': build_gutendex_resources(book),
            '_score': score,
            '_work_key': ''
        })
    return results


def fetch_openlibrary_best_doc(title, author=''):
    fields = ','.join([
        'key', 'title', 'author_name', 'first_publish_year', 'cover_i',
        'ratings_average', 'ratings_count', 'subject', 'ia', 'ebook_access'
    ])
    url = f"https://openlibrary.org/search.json?title={urllib.parse.quote(title)}&limit=10&fields={fields}"
    if author:
        url += f"&author={urllib.parse.quote(author)}"

    data = fetch_json(url, timeout=6)
    best_doc = None
    best_score = -1
    for doc in data.get('docs', [])[:10]:
        cand_title = doc.get('title', '')
        cand_author = ', '.join(doc.get('author_name', [])[:2]) if doc.get('author_name') else ''
        score = score_match(title, author, cand_title, cand_author)
        if doc.get('ratings_average'):
            score += 4
        if doc.get('cover_i'):
            score += 2
        if score > best_score:
            best_score = score
            best_doc = doc
    return best_doc


def fetch_googlebooks_best_item(title, author=''):
    query_parts = [f"intitle:{title}"]
    if author:
        query_parts.append(f"inauthor:{author}")
    query = urllib.parse.quote(' '.join(query_parts))
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=10&printType=books"
    data = fetch_json(url, timeout=6)

    best_item = None
    best_score = -1
    for item in (data.get('items', []) or [])[:10]:
        volume = item.get('volumeInfo', {})
        cand_title = volume.get('title', '')
        cand_author = ', '.join(volume.get('authors', [])[:2]) if volume.get('authors') else ''
        score = score_match(title, author, cand_title, cand_author)
        if volume.get('description'):
            score += 5
        if volume.get('imageLinks', {}).get('thumbnail'):
            score += 2
        if volume.get('averageRating'):
            score += 2
        if score > best_score:
            best_score = score
            best_item = item
    return best_item


def enrich_candidate_metadata(item, query_title='', query_author=''):
    enriched = dict(item)

    # 先尝试 Google Books 详情补充
    try:
        gb_item = fetch_googlebooks_best_item(
            enriched.get('title') or query_title,
            enriched.get('author') or query_author
        )
        if gb_item:
            volume = gb_item.get('volumeInfo', {})

            if not enriched.get('synopsis'):
                enriched['synopsis'] = str(volume.get('description', '')).strip()[:320]

            if (not enriched.get('category')) or enriched.get('category') == '文学小说':
                categories = volume.get('categories', [])[:4]
                mapped = map_category(categories)
                if mapped:
                    enriched['category'] = mapped

            if not enriched.get('cover'):
                image_links = volume.get('imageLinks', {}) or {}
                cover = image_links.get('thumbnail', '') or image_links.get('smallThumbnail', '')
                if cover.startswith('http://'):
                    cover = cover.replace('http://', 'https://', 1)
                enriched['cover'] = cover

            if (not enriched.get('rating')) and volume.get('averageRating') is not None:
                rating = to_float(volume.get('averageRating'))
                if rating:
                    enriched['rating'] = round(rating, 1)
                    enriched['ratingSource'] = 'Google Books'

            enriched['resources'] = merge_resources((enriched.get('resources') or []) + build_google_resources(gb_item))
    except Exception:
        pass

    # 再尝试 Open Library work 详情补充
    try:
        ol_doc = fetch_openlibrary_best_doc(
            enriched.get('title') or query_title,
            enriched.get('author') or query_author
        )
        if ol_doc:
            if not enriched.get('synopsis') and ol_doc.get('key'):
                enriched['synopsis'] = fetch_work_description(ol_doc.get('key'))

            if (not enriched.get('category')) or enriched.get('category') == '文学小说':
                enriched['category'] = map_category(ol_doc.get('subject', [])[:6])

            if not enriched.get('cover') and ol_doc.get('cover_i'):
                enriched['cover'] = f"https://covers.openlibrary.org/b/id/{ol_doc['cover_i']}-M.jpg"

            if (not enriched.get('rating')) and ol_doc.get('ratings_average') is not None:
                rating = to_float(ol_doc.get('ratings_average'))
                if rating:
                    enriched['rating'] = round(rating, 1)
                    enriched['ratingSource'] = 'Open Library'

            enriched['resources'] = merge_resources((enriched.get('resources') or []) + build_openlibrary_resources(ol_doc))
    except Exception:
        pass

    # 中文书补充：豆瓣简介与评分（最佳匹配）
    try:
        if contains_cjk(enriched.get('title') or query_title):
            if (not enriched.get('rating')) or (not has_real_synopsis(enriched.get('synopsis', ''))):
                douban = fetch_douban_best_metadata(
                    enriched.get('title') or query_title,
                    enriched.get('author') or query_author
                )
                if douban:
                    if (not has_real_synopsis(enriched.get('synopsis', ''))) and has_real_synopsis(douban.get('synopsis', '')):
                        enriched['synopsis'] = douban.get('synopsis', '')
                    if (not enriched.get('rating')) and douban.get('rating'):
                        enriched['rating'] = douban.get('rating')
                        enriched['ratingSource'] = douban.get('ratingSource', '豆瓣')
                    enriched['resources'] = merge_resources((enriched.get('resources') or []) + [douban.get('resource', {})])
                    if enriched.get('source'):
                        if '豆瓣' not in enriched['source']:
                            enriched['source'] = f"{enriched['source']} / 豆瓣"
                    else:
                        enriched['source'] = '豆瓣'
    except Exception:
        pass

    # 最后兜底：保证前端能拿到可展示的简介文本
    if not (enriched.get('synopsis') or '').strip():
        parts = []
        if enriched.get('author'):
            parts.append(f"作者：{enriched.get('author')}")
        if enriched.get('year'):
            parts.append(f"出版年份：{enriched.get('year')}")
        if enriched.get('category'):
            parts.append(f"分类：{enriched.get('category')}")
        if enriched.get('source'):
            parts.append(f"数据来源：{enriched.get('source')}")

        suffix = '；'.join(parts)
        if suffix:
            enriched['synopsis'] = f"暂无可公开抓取的详细简介。{suffix}。可点击下方资源链接查看详情页或在线预览。"
        else:
            enriched['synopsis'] = '暂无可公开抓取的详细简介，可点击下方资源链接查看详情页或在线预览。'

    return enriched


def merge_candidates(candidates):
    merged = {}
    for item in candidates:
        key = normalize_key(item.get('title', ''), item.get('author', ''))
        if not key:
            continue

        if key not in merged:
            merged[key] = item
            merged[key]['sources'] = [item.get('source', '')] if item.get('source') else []
            continue

        current = merged[key]
        if item.get('_score', 0) > current.get('_score', 0):
            preferred = item
            backup = current
        else:
            preferred = current
            backup = item

        combined = dict(preferred)
        combined['synopsis'] = preferred.get('synopsis') or backup.get('synopsis', '')
        if len(backup.get('synopsis', '')) > len(combined.get('synopsis', '')):
            combined['synopsis'] = backup.get('synopsis', '')

        if not combined.get('cover'):
            combined['cover'] = backup.get('cover', '')
        if not combined.get('rating') and backup.get('rating'):
            combined['rating'] = backup.get('rating')
            combined['ratingSource'] = backup.get('ratingSource', '')
        if not combined.get('year') and backup.get('year'):
            combined['year'] = backup.get('year')
        if not combined.get('category') or combined.get('category') == '文学小说':
            if backup.get('category'):
                combined['category'] = backup.get('category')

        combined['resources'] = merge_resources((current.get('resources') or []) + (item.get('resources') or []))

        src_set = set((current.get('sources') or []) + (item.get('sources') or []) + ([current.get('source')] if current.get('source') else []) + ([item.get('source')] if item.get('source') else []))
        combined['sources'] = [s for s in src_set if s]
        combined['source'] = ' / '.join(combined['sources'])

        merged[key] = combined

    return list(merged.values())


def search_book_info(title, author=""):
    """聚合多个公开 API 搜索书籍并合并结果。"""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(fetch_openlibrary_candidates, title, author),
                executor.submit(fetch_googlebooks_candidates, title, author),
                executor.submit(fetch_gutendex_candidates, title, author),
            ]

            all_candidates = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    all_candidates.extend(future.result() or [])
                except Exception:
                    continue

        if not all_candidates:
            return []

        merged = merge_candidates(all_candidates)
        for index, item in enumerate(merged[:8]):
            need_enrich = (
                not item.get('synopsis')
                or not item.get('cover')
                or (not item.get('rating'))
                or item.get('category') in ('', '文学小说')
            )
            if need_enrich and index < 6:
                merged[index] = enrich_candidate_metadata(item, title, author)
            elif (not item.get('synopsis')) and item.get('_work_key'):
                merged[index]['synopsis'] = fetch_work_description(item.get('_work_key'))

        merged.sort(
            key=lambda i: (
                1 if has_real_synopsis(i.get('synopsis', '')) else 0,
                i.get('_score', 0),
                i.get('rating') or 0
            ),
            reverse=True
        )
        results = []
        for item in merged[:8]:
            final_resources = append_discovery_resources(
                item.get('resources', []),
                item.get('title', ''),
                item.get('author', '')
            )
            results.append({
                'title': item.get('title', ''),
                'author': item.get('author', ''),
                'synopsis': item.get('synopsis', ''),
                'rating': item.get('rating'),
                'ratingSource': item.get('ratingSource', ''),
                'category': item.get('category', '文学小说'),
                'cover': item.get('cover', ''),
                'year': item.get('year'),
                'source': item.get('source', ''),
                'resources': final_resources
            })
        return results
    except Exception as e:
        return {'error': str(e)}


def fetch_json(url, timeout=6):
    req = urllib.request.Request(url, headers={'User-Agent': SEARCH_USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def fetch_work_description(work_key):
    if not work_key:
        return ''
    try:
        work_url = f"https://openlibrary.org{work_key}.json"
        work_data = fetch_json(work_url, timeout=5)
        desc = work_data.get('description', '')
        if isinstance(desc, dict):
            desc = desc.get('value', '')
        text = str(desc).strip()
        return text[:260] if text else ''
    except Exception:
        return ''


def map_category(subjects):
    if not subjects:
        return '文学小说'
    joined = ' '.join(subjects).lower()
    mapping = [
        ('science fiction fantasy dystopia', '科幻奇幻'),
        ('mystery detective crime thriller', '推理悬疑'),
        ('history biography memoir', '历史传记'),
        ('philosophy ethics', '哲学思想'),
        ('sociology politics culture society', '社会科学'),
        ('science physics biology chemistry', '自然科学'),
        ('psychology mental', '心理学'),
        ('business economics management finance', '经济管理'),
        ('computer technology programming ai', '科技'),
        ('art design music', '艺术设计'),
        ('health cooking lifestyle', '生活'),
    ]
    for keys, category in mapping:
        for keyword in keys.split():
            if keyword in joined:
                return category
    return '文学小说'


def autocomplete_book(query):
    if not query:
        return []
    suggestions = []
    seen = set()

    try:
        fields = 'title,author_name,first_publish_year'
        ol_url = f"https://openlibrary.org/search.json?q={urllib.parse.quote(query)}&limit=8&fields={fields}"
        ol_data = fetch_json(ol_url, timeout=5)
        for doc in ol_data.get('docs', [])[:8]:
            title = str(doc.get('title', '')).strip()
            if not title:
                continue
            author = ', '.join(doc.get('author_name', [])[:2]) if doc.get('author_name') else ''
            key = normalize_key(title, author)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append({
                'title': title,
                'author': author,
                'year': doc.get('first_publish_year'),
                'source': 'Open Library'
            })
    except Exception:
        pass

    try:
        gb_query = urllib.parse.quote(query)
        gb_url = f"https://www.googleapis.com/books/v1/volumes?q={gb_query}&maxResults=8&printType=books"
        gb_data = fetch_json(gb_url, timeout=5)
        for item in (gb_data.get('items', []) or [])[:8]:
            volume = item.get('volumeInfo', {})
            title = str(volume.get('title', '')).strip()
            if not title:
                continue
            author = ', '.join(volume.get('authors', [])[:2]) if volume.get('authors') else ''
            year = None
            published_date = str(volume.get('publishedDate', ''))
            if published_date[:4].isdigit():
                year = int(published_date[:4])
            key = normalize_key(title, author)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append({
                'title': title,
                'author': author,
                'year': year,
                'source': 'Google Books'
            })
    except Exception:
        pass

    return suggestions[:10]


def read_data():
    """读取数据文件"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        initial = {"books": []}
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial, f, ensure_ascii=False, indent=2)
        return initial
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_data(data):
    """写入数据文件"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class BookHandler(http.server.SimpleHTTPRequestHandler):
    """处理 API 和静态文件请求"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def log_message(self, format, *args):
        """简化日志输出"""
        pass

    def send_json(self, data, status=200):
        """发送 JSON 响应"""
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        """读取请求体 JSON"""
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode('utf-8'))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)

        if path == '/api/books':
            data = read_data()
            self.send_json(data['books'])
        elif path == '/api/search-book':
            # 搜索书籍信息
            title = query_params.get('title', [''])[0]
            author = query_params.get('author', [''])[0]
            if not title:
                self.send_json({"error": "请提供书名"}, 400)
                return
            results = search_book_info(title, author)
            self.send_json(results)
        elif path == '/api/search-suggest':
            query = query_params.get('q', [''])[0].strip()
            if len(query) < 2:
                self.send_json([])
                return
            self.send_json(autocomplete_book(query))
        elif path.startswith('/api/'):
            self.send_json({"error": "未找到"}, 404)
        else:
            # 静态文件
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 添加书籍
        if path == '/api/books':
            body = self.read_body()
            data = read_data()
            book = {
                "id": str(uuid.uuid4()),
                "title": body.get("title", ""),
                "author": body.get("author", ""),
                "synopsis": body.get("synopsis", ""),
                "rating": body.get("rating"),
                "ratingSource": body.get("ratingSource", ""),
                "category": body.get("category", "未分类"),
                "cover": body.get("cover", ""),
                "resources": body.get("resources", []),
                "addedBy": body.get("addedBy", "匿名"),
                "addedAt": datetime.now(timezone.utc).isoformat(),
                "status": "candidate",
                "votes": {},
                "reviews": []
            }
            data['books'].append(book)
            write_data(data)
            self.send_json(book)
            return

        # 投票
        parts = path.strip('/').split('/')
        if len(parts) == 4 and parts[0] == 'api' and parts[1] == 'books' and parts[3] == 'vote':
            book_id = parts[2]
            body = self.read_body()
            data = read_data()
            book = next((b for b in data['books'] if b['id'] == book_id), None)
            if not book:
                self.send_json({"error": "书籍未找到"}, 404)
                return
            user_id = body.get("userId", "匿名")
            if user_id in book.get('votes', {}):
                del book['votes'][user_id]
            else:
                if 'votes' not in book:
                    book['votes'] = {}
                book['votes'][user_id] = True
            write_data(data)
            self.send_json(book)
            return

        # 添加书评
        if len(parts) == 4 and parts[0] == 'api' and parts[1] == 'books' and parts[3] == 'reviews':
            book_id = parts[2]
            body = self.read_body()
            data = read_data()
            book = next((b for b in data['books'] if b['id'] == book_id), None)
            if not book:
                self.send_json({"error": "书籍未找到"}, 404)
                return
            review = {
                "id": str(uuid.uuid4()),
                "userId": body.get("userId", "匿名"),
                "content": body.get("content", ""),
                "rating": body.get("rating"),
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "comments": []
            }
            if 'reviews' not in book:
                book['reviews'] = []
            book['reviews'].append(review)
            write_data(data)
            self.send_json(review)
            return

        # 添加评论到书评
        if len(parts) == 6 and parts[0] == 'api' and parts[1] == 'books' and parts[3] == 'reviews' and parts[5] == 'comments':
            book_id = parts[2]
            review_id = parts[4]
            body = self.read_body()
            data = read_data()
            book = next((b for b in data['books'] if b['id'] == book_id), None)
            if not book:
                self.send_json({"error": "书籍未找到"}, 404)
                return
            review = next((r for r in book.get('reviews', []) if r['id'] == review_id), None)
            if not review:
                self.send_json({"error": "书评未找到"}, 404)
                return
            comment = {
                "id": str(uuid.uuid4()),
                "userId": body.get("userId", "匿名"),
                "content": body.get("content", ""),
                "createdAt": datetime.now(timezone.utc).isoformat()
            }
            if 'comments' not in review:
                review['comments'] = []
            review['comments'].append(comment)
            write_data(data)
            self.send_json(comment)
            return

        self.send_json({"error": "未找到"}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        parts = path.strip('/').split('/')

        # 更新书籍
        if len(parts) == 3 and parts[0] == 'api' and parts[1] == 'books':
            book_id = parts[2]
            body = self.read_body()
            data = read_data()
            book = next((b for b in data['books'] if b['id'] == book_id), None)
            if not book:
                self.send_json({"error": "书籍未找到"}, 404)
                return
            allowed = ['title', 'author', 'synopsis', 'rating', 'ratingSource', 'category', 'cover', 'status']
            for key in allowed:
                if key in body:
                    book[key] = body[key]
            write_data(data)
            self.send_json(book)
            return

        self.send_json({"error": "未找到"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        parts = path.strip('/').split('/')

        # 删除书籍
        if len(parts) == 3 and parts[0] == 'api' and parts[1] == 'books':
            book_id = parts[2]
            data = read_data()
            idx = next((i for i, b in enumerate(data['books']) if b['id'] == book_id), None)
            if idx is None:
                self.send_json({"error": "书籍未找到"}, 404)
                return
            removed = data['books'].pop(idx)
            write_data(data)
            self.send_json(removed)
            return

        # 删除书评
        if len(parts) == 5 and parts[0] == 'api' and parts[1] == 'books' and parts[3] == 'reviews':
            book_id = parts[2]
            review_id = parts[4]
            data = read_data()
            book = next((b for b in data['books'] if b['id'] == book_id), None)
            if not book:
                self.send_json({"error": "书籍未找到"}, 404)
                return
            idx = next((i for i, r in enumerate(book.get('reviews', [])) if r['id'] == review_id), None)
            if idx is None:
                self.send_json({"error": "书评未找到"}, 404)
                return
            book['reviews'].pop(idx)
            write_data(data)
            self.send_json({"success": True})
            return

        # 删除评论
        if len(parts) == 7 and parts[0] == 'api' and parts[1] == 'books' and parts[3] == 'reviews' and parts[5] == 'comments':
            book_id = parts[2]
            review_id = parts[4]
            comment_id = parts[6]
            data = read_data()
            book = next((b for b in data['books'] if b['id'] == book_id), None)
            if not book:
                self.send_json({"error": "书籍未找到"}, 404)
                return
            review = next((r for r in book.get('reviews', []) if r['id'] == review_id), None)
            if not review:
                self.send_json({"error": "书评未找到"}, 404)
                return
            idx = next((i for i, c in enumerate(review.get('comments', [])) if c['id'] == comment_id), None)
            if idx is None:
                self.send_json({"error": "评论未找到"}, 404)
                return
            review['comments'].pop(idx)
            write_data(data)
            self.send_json({"success": True})
            return

        self.send_json({"error": "未找到"}, 404)


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """支持多线程的 HTTP 服务器"""
    allow_reuse_address = True


if __name__ == '__main__':
    server = ThreadedServer(('0.0.0.0', PORT), BookHandler)
    print(f'📚 阅读计划管理工具已启动!')
    print(f'   本地访问: http://localhost:{PORT}')
    print(f'   按 Ctrl+C 停止服务器')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 服务器已停止')
        server.server_close()
