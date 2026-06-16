# Day 2 — Agent Tools & Interoperability with MCP

> **5-Day AI Agents: Intensive Vibe Coding Course With Google × Kaggle**

---

## ✅ What I Did Today

### 🎙️ Listened — Unit 2 Summary Podcast
*"Agent Tools & Interoperability with Model Context Protocol (MCP)"*  
→ [Watch on YouTube](https://www.youtube.com/watch?v=-arx8ems8Pw)

### 📄 Read — Whitepaper: Agent Tools & Interoperability
*How agents use external tools and functions to act beyond their training data — and how MCP standardises that connection layer.*  
→ [Read the Whitepaper on Kaggle](https://www.kaggle.com/whitepaper-agent-tools-and-interoperability?utm_medium=email&utm_source=gamma&utm_campaign=learn-intensive-assignment2-june-2026)

### 🛠️ Hands-On Tasks Completed
- **Configured Google Cloud Project** — Set up the cloud environment required to run and deploy agent-powered apps
- **Configured Antigravity 2.0** — Set up the Antigravity agent via both the **IDE** and **CLI**, getting familiar with both interfaces
- **Used Developer Knowledge via MCP** — Accessed developer documentation and context through MCP servers, letting the agent pull live knowledge during development
- **Hands-on with Antigravity CLI** — Used the `agy` CLI to scaffold, iterate, and build through agentic prompting

---

## 📋 Original Assignment

The Day 2 assignment was to build a web app using **Python Flask + vanilla HTML/JS/CSS** that:
- Fetches the **BigQuery Release Notes** from the official Google Cloud RSS feed (`https://docs.cloud.google.com/feeds/bigquery-release-notes.xml`)
- Displays them in a clean UI with a **refresh button + spinner**
- Allows selecting any specific update and **tweeting about it**

---

## ⚡ What I Actually Built — AURA//PAPER

Instead of the BigQuery release notes app, I took the same technical brief — **RSS feed ingestion → Flask backend → clean UI with refresh and share** — and applied it to something I personally wanted to use every day: a real-time AI/ML research aggregator.

The core architecture is identical to what the assignment asked for. The data source and domain are different.

**AURA//PAPER** is a full-stack Flask + SQLite web app that pulls research papers from three live sources, merges and deduplicates them, and serves them through a polished glassmorphism dark UI — **this is a v1 and will be upgraded in upcoming days.**

### Features
- **Three live data sources** aggregated simultaneously:
  - 📄 **arXiv RSS** — latest cs.CV, cs.LG, cs.AI, cs.CL papers (40 per refresh)
  - 🤗 **Hugging Face Daily Papers API** — community-curated picks with upvotes, GitHub repos, and AI-generated summaries
  - 🔬 **Major AI Labs filter** — OpenAI, DeepMind, Anthropic, Meta AI, Google Research, Microsoft Research papers auto-detected from arXiv
- **Smart deduplication** — papers appearing in multiple sources are merged into one enriched record
- **5-tab navigation** — All Papers / arXiv Feed / HF Daily / Major Labs / Bookmarks
- **Live search with debounce** — search across titles, abstracts, authors, and categories
- **Bookmark system** — star any paper, persisted in SQLite with auto-cleanup after 30 days
- **One-click X (Twitter) share** for any paper — directly inspired by the assignment's tweet requirement
- **AI Quick Insights** — HF-generated summaries surfaced inline when available
- **Real-time stats bar** — total cached, bookmarks, HF daily count, AI labs count
- **Glassmorphism dark UI** — custom CSS design system, no framework dependency

---

## 💡 Key Insight That Hit Hardest

> *"External tools are not add-ons to agents — they are the agent's hands. Without well-designed tool interfaces, an agent is just a language model talking to itself."*

The whitepaper reframes tools not as optional extensions but as the core mechanism by which agents cross the gap between knowing and doing. Configuring MCP in Antigravity and watching the agent pull developer knowledge in real time made this visceral — the agent stopped being a chatbot and started being a system that could *act*. That shift in mental model is what Day 2 is really about.

---

## 🧠 Key Learnings

### 1. Tools are how agents escape their training data
A model's knowledge is frozen at training time. Tools — API calls, code execution, database queries — are how agents access the present. Every `fetch_arxiv_papers()` call in AURA//PAPER is exactly this — breaking out of the static knowledge window into live data.

### 2. MCP is a standard contract, not just a plugin system
Model Context Protocol defines how an agent *discovers* what it can do, not just how it calls tools. Configuring MCP in Antigravity showed that tool discovery is as important as tool execution — an agent that can't enumerate its capabilities is flying blind.

### 3. IDE vs CLI — two modes, one agent
Setting up Antigravity via both the IDE and CLI revealed how the same agent behaves differently depending on the interface. The CLI is faster for iteration; the IDE gives visibility. Knowing when to use which is a real skill.

### 4. Developer knowledge through MCP changes the build loop
Pulling live developer documentation via MCP during the build — rather than copy-pasting from browser tabs — fundamentally changes how fast you can iterate. The agent had context I didn't have to provide manually.

### 5. The assignment prompt is a blueprint, not a constraint
The original assignment defined the tech stack (Flask, vanilla JS, RSS, refresh + share) and the pattern. Applying that same pattern to a different domain — AI research instead of BigQuery releases — produced something more personally useful while exercising all the same skills.

---

## 📁 File Structure & Explanations

```
day2/
├── README.md               ← This file — learnings and project overview
├── requirements.txt        ← All Python dependencies with exact pinned versions
├── .env.example            ← Environment variable template
└── src/
    ├── app.py              ← Entire Flask backend (routes, DB schema, fetchers, merge logic)
    ├── templates/
    │   └── index.html      ← Single-page app shell (Jinja2 + FontAwesome + Google Fonts)
    └── static/
        ├── css/
        │   └── style.css   ← Full custom design system (glassmorphism, animations, grid)
        └── js/
            └── main.js     ← Frontend controller (fetch, render, search, bookmark, share)
```

### Component Roles

| File | Purpose |
|------|---------|
| `src/app.py` | The entire backend in one file. Defines the SQLite schema (`papers` + `bookmarks` tables), three fetcher functions (`fetch_arxiv_papers`, `fetch_hf_daily_papers`, `fetch_major_labs_papers`), a `merge_and_save_papers()` orchestrator that deduplicates by arXiv ID, and 4 Flask routes. DB auto-seeds with live papers on first launch. |
| `src/templates/index.html` | SPA shell with 5-tab nav, stats bar, search box, loading/empty states, and the paper card grid. Fully server-rendered entry point; JS takes over from there. |
| `src/static/css/style.css` | 600+ line custom design system. CSS variables for the full colour palette, glassmorphism `.glass-panel` utility, animated background orbs, responsive card grid, badge system, toast notifications, and CSS-only 3D spinner. |
| `src/static/js/main.js` | Vanilla JS SPA controller. Handles tab switching, debounced search, API fetch calls, dynamic card rendering with expand/collapse abstracts, bookmark toggle with optimistic UI, and X/Twitter share intent. |
| `requirements.txt` | 14 pinned dependencies. Install with `pip install -r requirements.txt`. Core: Flask 3.1.3, feedparser 6.0.12, requests 2.34.2. |

---

## 🗂️ Data Flow

```
arXiv RSS API ──────┐
                    ├──► merge_and_save_papers() ──► SQLite papers.db ──► /api/papers ──► UI
HF Daily Papers ────┤         (dedup by arXiv ID,
API                 │          enrich, merge source flags,
                    │          auto-cleanup 30d+)
Major Labs ─────────┘
(arXiv filtered by
 lab name detection)
```

---

## 🚀 How to Run Locally

```bash
cd day2/src

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r ../requirements.txt

python app.py
```

Open [http://localhost:5000](http://localhost:5000) — the DB auto-seeds with live papers on first launch.

---

## 🔗 Resources

| Resource | Link |
|----------|------|
| 🎙️ Unit 2 Podcast | [YouTube](https://www.youtube.com/watch?v=-arx8ems8Pw) |
| 📄 Agent Tools & Interoperability Whitepaper | [Kaggle](https://www.kaggle.com/whitepaper-agent-tools-and-interoperability?utm_medium=email&utm_source=gamma&utm_campaign=learn-intensive-assignment2-june-2026) |
| 🛠️ Google AI Studio | [aistudio.google.com](https://aistudio.google.com) |
| 🤖 Antigravity 2.0 CLI | [antigravity.dev](https://antigravity.dev) |
| ☁️ Google Cloud Run | [cloud.google.com/run](https://cloud.google.com/run) |

---

*Part of the [5-Day AI Agents Intensive](../README.md) — Day 2 of 5*
