/* ============================================
   AppScript Bridge — Core JavaScript
   ============================================ */

// ── Theme ──
(function () {
    const saved = localStorage.getItem('asb-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
})();

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next    = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('asb-theme', next);
    _updateThemeBtn(next);
}

function _updateThemeBtn(theme) {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;
    if (theme === 'dark') {
        btn.innerHTML = '<i class="bi bi-sun"></i>';
        btn.title = 'Switch to light mode';
    } else {
        btn.innerHTML = '<i class="bi bi-moon-stars-fill"></i>';
        btn.title = 'Switch to dark mode';
    }
}

// ── API Helper ──
const api = {
    async request(method, url, data = null) {
        const opts = { method, headers: { 'Content-Type': 'application/json' } };
        if (data) opts.body = JSON.stringify(data);
        const resp = await fetch(url, opts);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ error: resp.statusText }));
            throw new Error(err.error || resp.statusText);
        }
        return resp.json();
    },
    get(url)           { return this.request('GET',    url); },
    post(url, data)    { return this.request('POST',   url, data); },
    put(url, data)     { return this.request('PUT',    url, data); },
    delete(url)        { return this.request('DELETE', url); },
};

// ── Toast ──
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const icon = type === 'error' ? 'bi-exclamation-circle' : 'bi-check-circle-fill';
    const toast = document.createElement('div');
    toast.className = `toast-custom ${type}`;
    toast.innerHTML = `<i class="bi ${icon}"></i> ${escapeHtml(message)}`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.25s ease';
        setTimeout(() => toast.remove(), 260);
    }, 3000);
}

// ── Delete Confirmation ──
let _deleteCallback = null;

function confirmDelete(message, callback) {
    document.getElementById('deleteMessage').textContent = message;
    _deleteCallback = callback;
    new bootstrap.Modal(document.getElementById('deleteModal')).show();
}

// ── Utilities ──
function escapeHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function timeAgo(dateString) {
    if (!dateString) return 'Never';
    const date    = new Date(dateString);
    const seconds = Math.floor((Date.now() - date) / 1000);
    if (seconds < 60)     return 'Just now';
    if (seconds < 3600)   return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400)  return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('show');
}

function toggleSidebarCollapse() {
    const sidebar = document.getElementById('sidebar');
    const collapseBtn = document.getElementById('sidebarCollapseBtn');
    if (!sidebar) return;
    const collapsed = sidebar.classList.toggle('collapsed');
    localStorage.setItem('asb-sidebar-collapsed', collapsed ? 'true' : 'false');
    
    if (collapsed) {
        document.documentElement.classList.add('sidebar-collapsed-pref');
    } else {
        document.documentElement.classList.remove('sidebar-collapsed-pref');
    }

    if (collapseBtn) {
        if (collapsed) {
            collapseBtn.innerHTML = '<i class="bi bi-dedent"></i>';
            collapseBtn.title = 'Expand Sidebar';
        } else {
            collapseBtn.innerHTML = '<i class="bi bi-indent"></i>';
            collapseBtn.title = 'Collapse Sidebar';
        }
    }
}

// ── DOMContentLoaded ──
document.addEventListener('DOMContentLoaded', () => {
    // Sync theme button icon on every page load
    _updateThemeBtn(document.documentElement.getAttribute('data-theme') || 'dark');

    // Restore sidebar collapse state
    const sidebar = document.getElementById('sidebar');
    const collapseBtn = document.getElementById('sidebarCollapseBtn');
    const isCollapsed = localStorage.getItem('asb-sidebar-collapsed') === 'true';
    if (sidebar) {
        if (isCollapsed) {
            sidebar.classList.add('collapsed');
            document.documentElement.classList.add('sidebar-collapsed-pref');
            if (collapseBtn) {
                collapseBtn.innerHTML = '<i class="bi bi-dedent"></i>';
                collapseBtn.title = 'Expand Sidebar';
            }
        } else {
            sidebar.classList.remove('collapsed');
            document.documentElement.classList.remove('sidebar-collapsed-pref');
            if (collapseBtn) {
                collapseBtn.innerHTML = '<i class="bi bi-indent"></i>';
                collapseBtn.title = 'Collapse Sidebar';
            }
        }
    }

    // Delete modal confirm
    const deleteBtn = document.getElementById('deleteConfirmBtn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', async () => {
            if (_deleteCallback) {
                try { await _deleteCallback(); }
                catch (e) { showToast(e.message, 'error'); }
            }
            bootstrap.Modal.getInstance(document.getElementById('deleteModal'))?.hide();
            _deleteCallback = null;
        });
    }

    // Restore collapsible sidebar tree states on load
    document.querySelectorAll('.tree-workspace-content, .tree-project-content').forEach(el => {
        const id = el.id.replace('content-', '');
        const state = localStorage.getItem('sidebar-' + id);
        const chevron = document.getElementById('chevron-' + id);
        if (state === 'collapsed') {
            el.style.display = 'none';
            if (chevron) chevron.classList.add('collapsed');
        } else {
            el.style.display = 'block';
            if (chevron) chevron.classList.remove('collapsed');
        }
    });
});

function toggleSidebarNode(id, event) {
    if (event) {
        // Prevent event from bubbling up to parents
        event.stopPropagation();
    }
    const content = document.getElementById('content-' + id);
    const chevron = document.getElementById('chevron-' + id);
    if (!content || !chevron) return;
    const isCollapsed = content.style.display === 'none';
    if (isCollapsed) {
        content.style.display = 'block';
        chevron.classList.remove('collapsed');
        localStorage.setItem('sidebar-' + id, 'expanded');
    } else {
        content.style.display = 'none';
        chevron.classList.add('collapsed');
        localStorage.setItem('sidebar-' + id, 'collapsed');
    }
}
