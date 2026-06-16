/* ==========================================================================
   AURA//PAPER - FRONTEND CONTROLLER
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // Application State
    let activeSource = 'all';
    let searchQuery = '';
    let papersData = [];
    let searchTimeout = null;

    // DOM Elements
    const papersGrid = document.getElementById('papers-grid');
    const searchInput = document.getElementById('search-input');
    const clearSearchBtn = document.getElementById('clear-search-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    const feedLoading = document.getElementById('feed-loading');
    const feedEmpty = document.getElementById('feed-empty');
    const emptyActionBtn = document.getElementById('empty-action-btn');
    const tabItems = document.querySelectorAll('.tab-item');
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');

    // Stats Elements
    const statTotal = document.getElementById('stat-total');
    const statBookmarks = document.getElementById('stat-bookmarks');
    const statHf = document.getElementById('stat-hf');
    const statLabs = document.getElementById('stat-labs');

    // Initialize
    init();

    function init() {
        // Fetch Initial Papers
        fetchPapers();

        // Setup Tab Event Listeners
        tabItems.forEach(tab => {
            tab.addEventListener('click', () => {
                tabItems.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                activeSource = tab.getAttribute('data-source');
                fetchPapers();
            });
        });

        // Search Input Handling with Debounce
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value;
            
            // Show/hide clear button
            if (searchQuery.length > 0) {
                clearSearchBtn.style.display = 'block';
            } else {
                clearSearchBtn.style.display = 'none';
            }

            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                fetchPapers();
            }, 300);
        });

        // Clear Search Button
        clearSearchBtn.addEventListener('click', () => {
            searchInput.value = '';
            searchQuery = '';
            clearSearchBtn.style.display = 'none';
            fetchPapers();
            searchInput.focus();
        });

        // Refresh Button
        refreshBtn.addEventListener('click', () => {
            triggerRefresh();
        });

        // Empty State Action Button (Reset Filters)
        emptyActionBtn.addEventListener('click', () => {
            searchInput.value = '';
            searchQuery = '';
            clearSearchBtn.style.display = 'none';
            activeSource = 'all';
            tabItems.forEach(t => {
                t.classList.remove('active');
                if (t.getAttribute('data-source') === 'all') {
                    t.classList.add('active');
                }
            });
            fetchPapers();
        });
    }

    // Toast Notification helper
    function showToast(message, type = 'info') {
        toastMessage.textContent = message;
        toast.className = `toast glass-panel show ${type}`;
        
        // Dynamic Toast Icon
        const icon = toast.querySelector('.toast-icon');
        icon.className = 'fa-solid toast-icon';
        if (type === 'success') {
            icon.classList.add('fa-circle-check');
        } else if (type === 'error') {
            icon.classList.add('fa-circle-xmark');
        } else {
            icon.classList.add('fa-circle-info');
        }

        setTimeout(() => {
            toast.classList.remove('show');
        }, 4000);
    }

    // Fetch Papers from Flask API
    function fetchPapers() {
        // Show loading spinner
        feedLoading.style.display = 'flex';
        papersGrid.style.display = 'none';
        feedEmpty.style.display = 'none';

        const url = `/api/papers?source=${activeSource}&search=${encodeURIComponent(searchQuery)}`;
        
        fetch(url)
            .then(res => res.json())
            .then(data => {
                feedLoading.style.display = 'none';
                if (data.status === 'success') {
                    papersData = data.papers;
                    
                    // Update stats if backend provides them, else calculate locally
                    if (data.stats) {
                        statTotal.textContent = data.stats.total || 0;
                        statBookmarks.textContent = data.stats.bookmarks || 0;
                        statHf.textContent = data.stats.hf || 0;
                        statLabs.textContent = data.stats.labs || 0;
                    } else {
                        // local fallback calculation from current payload
                        statTotal.textContent = papersData.length;
                        statBookmarks.textContent = papersData.filter(p => p.bookmarked).length;
                        statHf.textContent = papersData.filter(p => p.is_hf).length;
                        statLabs.textContent = papersData.filter(p => p.is_labs).length;
                    }

                    renderPapers();
                } else {
                    showToast(data.message || 'Error loading papers', 'error');
                }
            })
            .catch(err => {
                feedLoading.style.display = 'none';
                showToast('Failed to connect to research feed', 'error');
                console.error(err);
            });
    }

    // Trigger Scraper Refresh
    function triggerRefresh() {
        if (refreshBtn.classList.contains('loading')) return;

        refreshBtn.classList.add('loading');
        showToast('Fetching latest research from arXiv and Hugging Face...', 'info');

        fetch('/api/refresh', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                refreshBtn.classList.remove('loading');
                if (data.status === 'success') {
                    showToast('Feed updated successfully!', 'success');
                    fetchPapers();
                } else {
                    showToast(data.message || 'Refresh failed', 'error');
                }
            })
            .catch(err => {
                refreshBtn.classList.remove('loading');
                showToast('Network error during refresh', 'error');
                console.error(err);
            });
    }

    // Render Papers Grid
    function renderPapers() {
        papersGrid.innerHTML = '';
        
        if (papersData.length === 0) {
            papersGrid.style.display = 'none';
            feedEmpty.style.display = 'flex';
            
            // Customize empty message based on active source/search
            if (searchQuery) {
                document.getElementById('empty-title').textContent = 'No matching search results';
                document.getElementById('empty-desc').textContent = `We couldn't find anything matching "${searchQuery}".`;
            } else if (activeSource === 'bookmarks') {
                document.getElementById('empty-title').textContent = 'No bookmarks saved yet';
                document.getElementById('empty-desc').textContent = 'Click the star icon on any research paper to save it here.';
            } else {
                document.getElementById('empty-title').textContent = 'No papers available';
                document.getElementById('empty-desc').textContent = 'Click the Refresh button to fetch latest papers.';
            }
            return;
        }

        feedEmpty.style.display = 'none';
        papersGrid.style.display = 'grid';

        papersData.forEach(paper => {
            const card = document.createElement('article');
            card.className = 'paper-card glass-panel';
            card.setAttribute('data-id', paper.id);

            // Date Formatting
            const dateStr = paper.published_date;
            let formattedDate = 'Recent';
            try {
                // format YYYY-MM-DD HH:MM:SS
                const dateParts = dateStr.split(' ')[0].split('-');
                const dateObj = new Date(dateParts[0], dateParts[1] - 1, dateParts[2]);
                formattedDate = dateObj.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric'
                });
            } catch (e) {
                formattedDate = dateStr;
            }

            // Badges logic
            let badgeHtml = '';
            if (paper.lab_name) {
                badgeHtml = `<span class="badge badge-labs"><i class="fa-solid fa-flask"></i> ${paper.lab_name}</span>`;
            } else if (paper.is_hf && paper.is_arxiv) {
                badgeHtml = `<span class="badge badge-hf"><i class="fa-brands fa-hugging-face"></i> HF + arXiv</span>`;
            } else if (paper.is_hf) {
                badgeHtml = `<span class="badge badge-hf"><i class="fa-brands fa-hugging-face"></i> HF Daily</span>`;
            } else if (paper.is_arxiv) {
                badgeHtml = `<span class="badge badge-arxiv"><i class="fa-solid fa-graduation-cap"></i> arXiv</span>`;
            }

            // Authors preview
            const authorsList = paper.authors.join(', ');
            let authorsHtml = authorsList;
            if (paper.authors.length > 5) {
                authorsHtml = paper.authors.slice(0, 5).join(', ') + ` <em>et al.</em>`;
            }

            // Category tag render (limit to 5 tags to avoid clutter)
            let tagsHtml = '';
            if (paper.categories && paper.categories.length > 0) {
                // Remove duplicates and limit
                const uniqueTags = [...new Set(paper.categories)].slice(0, 5);
                tagsHtml = uniqueTags.map(cat => `<span class="category-tag">${cat}</span>`).join('');
            }

            // AI summary block (if available from HF)
            let aiSummaryHtml = '';
            if (paper.ai_summary) {
                aiSummaryHtml = `
                    <div class="ai-summary-block">
                        <strong><i class="fa-solid fa-circle-nodes"></i> Quick Insight:</strong>
                        ${paper.ai_summary}
                    </div>
                `;
            }

            // Links group
            let linksHtml = '';
            if (paper.arxiv_link) {
                linksHtml += `<a href="${paper.arxiv_link}" target="_blank" class="card-link link-pdf" title="View PDF on arXiv"><i class="fa-solid fa-file-pdf"></i> arXiv</a>`;
            }
            if (paper.hf_link) {
                linksHtml += `<a href="${paper.hf_link}" target="_blank" class="card-link link-hf" title="View Hugging Face page"><i class="fa-brands fa-hugging-face"></i> HF Page</a>`;
            }
            if (paper.github_repo) {
                linksHtml += `<a href="${paper.github_repo}" target="_blank" class="card-link link-git" title="View code repo"><i class="fa-brands fa-github"></i> Code</a>`;
            }

            // Upvotes count for HF
            let upvotesHtml = '';
            if (paper.is_hf && paper.upvotes > 0) {
                upvotesHtml = `<span class="card-link" style="color: var(--accent-yellow); font-weight:600;"><i class="fa-solid fa-fire"></i> ${paper.upvotes}</span>`;
            }

            // Tweet Share Content
            const tweetText = `Check out this AI research paper: "${paper.title}" ${paper.arxiv_link || paper.hf_link || ''} via @AuraPaper`;

            card.innerHTML = `
                <div>
                    <div class="card-header-meta">
                        <div class="pub-date"><i class="fa-regular fa-calendar"></i> ${formattedDate}</div>
                        <div>${badgeHtml}</div>
                    </div>
                    
                    <a href="${paper.arxiv_link || paper.hf_link}" target="_blank" class="paper-title">${paper.title}</a>
                    
                    <div class="paper-authors">
                        By <span>${authorsHtml}</span>
                    </div>
                    
                    <div class="abstract-container">
                        <div class="abstract-text collapsed" id="abstract-${paper.id}">
                            ${paper.summary}
                        </div>
                        ${paper.summary.length > 200 ? `
                            <button class="read-more-btn" data-id="${paper.id}">
                                <span>Read More</span> <i class="fa-solid fa-chevron-down"></i>
                            </button>
                        ` : ''}
                    </div>

                    ${aiSummaryHtml}
                    
                    <div class="category-row">
                        ${tagsHtml}
                    </div>
                </div>
                
                <div class="card-footer-actions">
                    <div class="links-group">
                        ${linksHtml}
                        ${upvotesHtml}
                    </div>
                    
                    <div class="social-group">
                        <button class="social-btn btn-share" data-tweet="${encodeURIComponent(tweetText)}" title="Share on X (Twitter)">
                            <i class="fa-brands fa-x-twitter"></i>
                        </button>
                        <button class="social-btn btn-bookmark ${paper.bookmarked ? 'active' : ''}" data-id="${paper.id}" title="${paper.bookmarked ? 'Remove Bookmark' : 'Bookmark Paper'}">
                            <i class="${paper.bookmarked ? 'fa-solid' : 'fa-regular'} fa-star"></i>
                        </button>
                    </div>
                </div>
            `;

            // Attach Read More Expand Handler
            const readMoreBtn = card.querySelector('.read-more-btn');
            if (readMoreBtn) {
                readMoreBtn.addEventListener('click', () => {
                    const abstractText = card.querySelector(`#abstract-${paper.id}`);
                    const icon = readMoreBtn.querySelector('i');
                    const textSpan = readMoreBtn.querySelector('span');

                    if (abstractText.classList.contains('collapsed')) {
                        abstractText.classList.remove('collapsed');
                        abstractText.classList.add('expanded');
                        textSpan.textContent = 'Collapse';
                        icon.className = 'fa-solid fa-chevron-up';
                    } else {
                        abstractText.classList.remove('expanded');
                        abstractText.classList.add('collapsed');
                        textSpan.textContent = 'Read More';
                        icon.className = 'fa-solid fa-chevron-down';
                    }
                });
            }

            // Attach Bookmark Toggle Handler
            const bookmarkBtn = card.querySelector('.btn-bookmark');
            bookmarkBtn.addEventListener('click', () => {
                toggleBookmark(paper.id, bookmarkBtn);
            });

            // Attach Tweet/X Share Handler
            const shareBtn = card.querySelector('.btn-share');
            shareBtn.addEventListener('click', () => {
                const tweetContent = decodeURIComponent(shareBtn.getAttribute('data-tweet'));
                const shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(tweetContent)}`;
                window.open(shareUrl, '_blank', 'width=600,height=400,resizable=yes,scrollbars=yes');
            });

            papersGrid.appendChild(card);
        });
    }

    // Toggle Bookmarking Action
    function toggleBookmark(paperId, btnElement) {
        fetch('/api/bookmark', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const isBookmarked = data.bookmarked;
                
                // Toggle visual classes
                if (isBookmarked) {
                    btnElement.classList.add('active');
                    btnElement.querySelector('i').className = 'fa-solid fa-star';
                    showToast('Paper bookmarked successfully!', 'success');
                } else {
                    btnElement.classList.remove('active');
                    btnElement.querySelector('i').className = 'fa-regular fa-star';
                    showToast('Bookmark removed.', 'info');
                    
                    // If we are currently on the Bookmarks tab, re-fetch or remove card dynamically
                    if (activeSource === 'bookmarks') {
                        // remove card from view smoothly
                        const card = btnElement.closest('.paper-card');
                        card.style.opacity = '0';
                        card.style.transform = 'scale(0.9)';
                        setTimeout(() => {
                            fetchPapers(); // re-fetch to handle empty state and updates correctly
                        }, 300);
                    }
                }

                // Increment / Decrement active bookmark stat counter dynamically
                const currentBookmarks = parseInt(statBookmarks.textContent);
                statBookmarks.textContent = isBookmarked ? currentBookmarks + 1 : Math.max(0, currentBookmarks - 1);

                // Update paper object in local state
                const targetPaper = papersData.find(p => p.id === paperId);
                if (targetPaper) targetPaper.bookmarked = isBookmarked;

            } else {
                showToast(data.message || 'Failed to toggle bookmark', 'error');
            }
        })
        .catch(err => {
            showToast('Error connecting to database', 'error');
            console.error(err);
        });
    }
});
