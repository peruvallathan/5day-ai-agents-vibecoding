import os
import json
import sqlite3
from datetime import datetime
import requests
import feedparser
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
app.secret_key = os.urandom(24)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'papers.db')

CATEGORY_MAPPING = {
    'cs.CV': 'Computer Vision',
    'cs.LG': 'Machine Learning',
    'cs.AI': 'Artificial Intelligence',
    'cs.CL': 'Natural Language Processing',
    'cs.NE': 'Neural Computing',
    'cs.RO': 'Robotics',
    'cs.IR': 'Information Retrieval',
    'cs.HC': 'Human-Computer Interaction',
    'stat.ML': 'Machine Learning (Stat)'
}

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT,
            summary TEXT,
            published_date TEXT,
            arxiv_link TEXT,
            hf_link TEXT,
            source TEXT,
            categories TEXT,
            upvotes INTEGER DEFAULT 0,
            github_repo TEXT,
            ai_summary TEXT,
            ai_keywords TEXT,
            is_arxiv INTEGER DEFAULT 0,
            is_hf INTEGER DEFAULT 0,
            is_labs INTEGER DEFAULT 0,
            lab_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            paper_id TEXT PRIMARY KEY,
            bookmarked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paper_id) REFERENCES papers (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def clean_arxiv_id(url_or_id):
    if '/' in url_or_id:
        base = url_or_id.split('/')[-1]
    else:
        base = url_or_id
    
    # Remove version suffix (e.g. 2606.17056v1 -> 2606.17056)
    if 'v' in base:
        parts = base.split('v')
        if parts[-1].isdigit():
            base = 'v'.join(parts[:-1])
    return base.strip()

def normalize_date_for_db(date_str):
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        clean_str = date_str.replace('Z', '').replace('T', ' ')
        if '.' in clean_str:
            clean_str = clean_str.split('.')[0]
        dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            # Try parsing date-only string e.g. 2026-06-15
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d 00:00:00")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def detect_ai_lab(title, summary, authors_list):
    text = f"{title} {summary} {' '.join(authors_list)}".lower()
    if 'openai' in text:
        return 'OpenAI'
    elif 'deepmind' in text:
        return 'Google DeepMind'
    elif 'anthropic' in text:
        return 'Anthropic'
    elif 'meta ai' in text or 'meta research' in text or ('meta' in text and 'ai' in text):
        return 'Meta AI'
    elif 'microsoft research' in text or ('microsoft' in text and 'research' in text):
        return 'Microsoft Research'
    elif 'google research' in text or ('google' in text and 'research' in text):
        return 'Google Research'
    return None

def fetch_arxiv_papers():
    # Fetch recent AI/ML papers from arXiv
    url = 'http://export.arxiv.org/api/query?search_query=cat:cs.CV+OR+cat:cs.LG+OR+cat:cs.AI+OR+cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=40'
    try:
        feed = feedparser.parse(url)
        papers = []
        for entry in feed.entries:
            pid = clean_arxiv_id(entry.id)
            title = entry.title.replace('\n', ' ').strip()
            authors = [a.name for a in entry.authors] if hasattr(entry, 'authors') else []
            summary = entry.summary.replace('\n', ' ').strip()
            published = normalize_date_for_db(entry.published)
            
            arxiv_link = entry.link
            for link in entry.links:
                if link.get('title') == 'pdf':
                    arxiv_link = link.get('href')
                    break
            
            categories = []
            if hasattr(entry, 'tags'):
                for t in entry.tags:
                    term = t.term
                    categories.append(CATEGORY_MAPPING.get(term, term))
            categories = list(set(categories))
            
            papers.append({
                'id': pid,
                'title': title,
                'authors': authors,
                'summary': summary,
                'published_date': published,
                'arxiv_link': arxiv_link,
                'hf_link': '',
                'categories': categories,
                'upvotes': 0,
                'github_repo': '',
                'ai_summary': '',
                'ai_keywords': [],
                'is_arxiv': 1,
                'is_hf': 0,
                'is_labs': 1 if detect_ai_lab(title, summary, authors) else 0,
                'lab_name': detect_ai_lab(title, summary, authors)
            })
        return papers
    except Exception as e:
        print(f"Error fetching arXiv: {e}")
        return []

def fetch_major_labs_papers():
    # Fetch papers from major AI labs (OpenAI, DeepMind, Anthropic, Google, Meta, Microsoft)
    query = '(all:OpenAI+OR+all:DeepMind+OR+all:Anthropic+OR+all:"Meta+AI"+OR+all:"Google+Research"+OR+all:"Microsoft+Research")'
    url = f'http://export.arxiv.org/api/query?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results=30'
    try:
        feed = feedparser.parse(url)
        papers = []
        for entry in feed.entries:
            pid = clean_arxiv_id(entry.id)
            title = entry.title.replace('\n', ' ').strip()
            authors = [a.name for a in entry.authors] if hasattr(entry, 'authors') else []
            summary = entry.summary.replace('\n', ' ').strip()
            published = normalize_date_for_db(entry.published)
            
            lab = detect_ai_lab(title, summary, authors)
            if not lab:
                continue
                
            arxiv_link = entry.link
            for link in entry.links:
                if link.get('title') == 'pdf':
                    arxiv_link = link.get('href')
                    break
            
            categories = []
            if hasattr(entry, 'tags'):
                for t in entry.tags:
                    term = t.term
                    categories.append(CATEGORY_MAPPING.get(term, term))
            categories = list(set(categories))
            
            papers.append({
                'id': pid,
                'title': title,
                'authors': authors,
                'summary': summary,
                'published_date': published,
                'arxiv_link': arxiv_link,
                'hf_link': '',
                'categories': categories,
                'upvotes': 0,
                'github_repo': '',
                'ai_summary': '',
                'ai_keywords': [],
                'is_arxiv': 1,
                'is_hf': 0,
                'is_labs': 1,
                'lab_name': lab
            })
        return papers
    except Exception as e:
        print(f"Error fetching labs from arXiv: {e}")
        return []

def fetch_hf_daily_papers():
    # Fetch papers from Hugging Face Daily Papers API
    url = 'https://huggingface.co/api/daily_papers'
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []
        data = response.json()
        papers = []
        for item in data:
            paper_details = item.get('paper', {})
            arxiv_id = paper_details.get('id')
            if not arxiv_id:
                continue
            
            pid = clean_arxiv_id(arxiv_id)
            title = paper_details.get('title', '').replace('\n', ' ').strip()
            
            authors = []
            for a in paper_details.get('authors', []):
                if isinstance(a, dict) and a.get('name'):
                    authors.append(a.get('name'))
                elif isinstance(a, str):
                    authors.append(a)
                    
            summary = paper_details.get('summary', '').replace('\n', ' ').strip()
            published = normalize_date_for_db(paper_details.get('publishedAt') or item.get('publishedAt'))
            
            upvotes = paper_details.get('upvotes') or item.get('upvotes') or 0
            if upvotes is None or upvotes == 'None':
                upvotes = 0
            
            github_repo = paper_details.get('githubRepo') or ''
            ai_summary = paper_details.get('ai_summary') or ''
            ai_keywords = paper_details.get('ai_keywords') or []
            if not isinstance(ai_keywords, list):
                ai_keywords = []
                
            categories = ["Hugging Face Daily"]
            if ai_keywords:
                categories.extend(ai_keywords)
            
            arxiv_link = f"https://arxiv.org/abs/{pid}"
            hf_link = f"https://huggingface.co/papers/{pid}"
            
            papers.append({
                'id': pid,
                'title': title,
                'authors': authors,
                'summary': summary,
                'published_date': published,
                'arxiv_link': arxiv_link,
                'hf_link': hf_link,
                'categories': categories,
                'upvotes': int(upvotes),
                'github_repo': github_repo,
                'ai_summary': ai_summary,
                'ai_keywords': ai_keywords,
                'is_arxiv': 1 if pid.replace('.', '').isdigit() else 0,
                'is_hf': 1,
                'is_labs': 1 if detect_ai_lab(title, summary, authors) else 0,
                'lab_name': detect_ai_lab(title, summary, authors)
            })
        return papers
    except Exception as e:
        print(f"Error fetching Hugging Face daily papers: {e}")
        return []

def merge_and_save_papers():
    arxiv_papers = fetch_arxiv_papers()
    labs_papers = fetch_major_labs_papers()
    hf_papers = fetch_hf_daily_papers()
    
    merged = {}
    
    def add_or_merge(p):
        pid = p['id']
        if pid not in merged:
            merged[pid] = p
        else:
            existing = merged[pid]
            existing['is_arxiv'] = existing['is_arxiv'] or p['is_arxiv']
            existing['is_hf'] = existing['is_hf'] or p['is_hf']
            existing['is_labs'] = existing['is_labs'] or p['is_labs']
            
            if p['lab_name'] and not existing['lab_name']:
                existing['lab_name'] = p['lab_name']
                existing['is_labs'] = 1
                
            if p['hf_link'] and not existing['hf_link']:
                existing['hf_link'] = p['hf_link']
                
            if p['github_repo'] and not existing['github_repo']:
                existing['github_repo'] = p['github_repo']
                
            if p['ai_summary'] and not existing['ai_summary']:
                existing['ai_summary'] = p['ai_summary']
                
            if p['ai_keywords'] and not existing['ai_keywords']:
                existing['ai_keywords'] = p['ai_keywords']
                
            if p['upvotes'] > existing['upvotes']:
                existing['upvotes'] = p['upvotes']
                
            cats = list(set(existing['categories'] + p['categories']))
            existing['categories'] = cats
            
            # Prefer more specific timestamps
            if len(p['published_date']) > len(existing['published_date']):
                existing['published_date'] = p['published_date']
                
    for p in arxiv_papers:
        add_or_merge(p)
    for p in labs_papers:
        add_or_merge(p)
    for p in hf_papers:
        add_or_merge(p)
        
    conn = get_db()
    cursor = conn.cursor()
    
    inserted_count = 0
    for pid, p in merged.items():
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO papers (
                    id, title, authors, summary, published_date, arxiv_link, hf_link,
                    source, categories, upvotes, github_repo, ai_summary, ai_keywords,
                    is_arxiv, is_hf, is_labs, lab_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pid,
                p['title'],
                json.dumps(p['authors']),
                p['summary'],
                p['published_date'],
                p['arxiv_link'],
                p['hf_link'],
                'arxiv' if p['is_arxiv'] and not p['is_hf'] and not p['is_labs'] else (
                    'huggingface' if p['is_hf'] and not p['is_labs'] else 'ailabs'
                ),
                json.dumps(p['categories']),
                p['upvotes'],
                p['github_repo'],
                p['ai_summary'],
                json.dumps(p['ai_keywords']),
                p['is_arxiv'],
                p['is_hf'],
                p['is_labs'],
                p['lab_name']
            ))
            inserted_count += 1
        except Exception as db_err:
            print(f"DB Error inserting paper {pid}: {db_err}")
            
    # Clean up non-bookmarked papers older than 30 days
    cursor.execute('''
        DELETE FROM papers 
        WHERE id NOT IN (SELECT paper_id FROM bookmarks)
        AND created_at < datetime('now', '-30 days')
    ''')
    
    conn.commit()
    conn.close()
    return inserted_count

def check_and_seed_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM papers")
    count = cursor.fetchone()[0]
    conn.close()
    if count == 0:
        print("Database is empty. Seeding with initial papers...")
        try:
            merge_and_save_papers()
            print("Database seeded.")
        except Exception as e:
            print(f"Failed to seed database: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/papers')
def get_papers():
    source = request.args.get('source', 'all')
    search_query = request.args.get('search', '').strip().lower()
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = '''
        SELECT p.*, (b.paper_id IS NOT NULL) as bookmarked
        FROM papers p
        LEFT JOIN bookmarks b ON p.id = b.paper_id
    '''
    conditions = []
    
    if source == 'arxiv':
        conditions.append("p.is_arxiv = 1")
    elif source == 'huggingface':
        conditions.append("p.is_hf = 1")
    elif source == 'ailabs':
        conditions.append("p.is_labs = 1")
    elif source == 'bookmarks':
        conditions.append("b.paper_id IS NOT NULL")
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY p.published_date DESC, p.created_at DESC LIMIT 100"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    papers = []
    for r in rows:
        try:
            authors = json.loads(r['authors'])
        except Exception:
            authors = [a.strip() for a in r['authors'].split(',')] if r['authors'] else []
            
        try:
            categories = json.loads(r['categories'])
        except Exception:
            categories = [c.strip() for c in r['categories'].split(',')] if r['categories'] else []
            
        try:
            ai_keywords = json.loads(r['ai_keywords'])
        except Exception:
            ai_keywords = []
            
        papers.append({
            'id': r['id'],
            'title': r['title'],
            'authors': authors,
            'summary': r['summary'],
            'published_date': r['published_date'],
            'arxiv_link': r['arxiv_link'],
            'hf_link': r['hf_link'],
            'source': r['source'],
            'categories': categories,
            'upvotes': r['upvotes'],
            'github_repo': r['github_repo'],
            'ai_summary': r['ai_summary'],
            'ai_keywords': ai_keywords,
            'is_arxiv': r['is_arxiv'],
            'is_hf': r['is_hf'],
            'is_labs': r['is_labs'],
            'lab_name': r['lab_name'],
            'bookmarked': bool(r['bookmarked'])
        })
    # Fetch statistics
    cursor.execute("SELECT COUNT(*) FROM papers")
    total_papers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bookmarks")
    total_bookmarks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM papers WHERE is_hf = 1")
    total_hf = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM papers WHERE is_labs = 1")
    total_labs = cursor.fetchone()[0]
    
    conn.close()
    
    if search_query:
        filtered_papers = []
        for p in papers:
            title_match = search_query in p['title'].lower()
            summary_match = search_query in p['summary'].lower()
            author_match = any(search_query in a.lower() for a in p['authors'])
            cat_match = any(search_query in c.lower() for c in p['categories'])
            if title_match or summary_match or author_match or cat_match:
                filtered_papers.append(p)
        papers = filtered_papers
        
    return jsonify({
        'status': 'success', 
        'papers': papers,
        'stats': {
            'total': total_papers,
            'bookmarks': total_bookmarks,
            'hf': total_hf,
            'labs': total_labs
        }
    })


@app.route('/api/bookmark', methods=['POST'])
def toggle_bookmark():
    data = request.json or {}
    paper_id = data.get('paper_id')
    if not paper_id:
        return jsonify({'status': 'error', 'message': 'Missing paper_id'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM bookmarks WHERE paper_id = ?", (paper_id,))
    exists = cursor.fetchone()
    
    if exists:
        cursor.execute("DELETE FROM bookmarks WHERE paper_id = ?", (paper_id,))
        bookmarked = False
    else:
        # Check if paper actually exists in our papers table to respect foreign keys
        cursor.execute("SELECT 1 FROM papers WHERE id = ?", (paper_id,))
        paper_exists = cursor.fetchone()
        if not paper_exists:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Paper not found in database'}), 404
            
        cursor.execute("INSERT INTO bookmarks (paper_id) VALUES (?)", (paper_id,))
        bookmarked = True
        
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'bookmarked': bookmarked})

@app.route('/api/refresh', methods=['POST'])
def refresh_papers():
    try:
        count = merge_and_save_papers()
        return jsonify({
            'status': 'success', 
            'message': f'Successfully updated database. Added/merged papers.',
            'count': count
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    init_db()
    check_and_seed_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
