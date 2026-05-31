/* ========================================
   PESQUISA ELEITORAL 2026 — APP.JS
   JavaScript do lado cliente (Flask MVC)
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    initRefreshBtn();
    initFlashAutoClose();
    initTemaCheckboxes();
});

/* ── Tema claro / escuro ─────────────────── */
function initTheme() {
    const btn = document.getElementById('themeToggle');
    const apply = (theme) => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('eleitoral-theme', theme);
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.content = theme === 'light' ? '#f1f5f9' : '#0a0e1a';
        }
        document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
    };

    btn?.addEventListener('click', () => {
        const cur = document.documentElement.getAttribute('data-theme') || 'dark';
        apply(cur === 'dark' ? 'light' : 'dark');
        if (document.querySelector('canvas')) {
            window.location.reload();
        }
    });
}

window.getChartTheme = function getChartTheme() {
    const s = getComputedStyle(document.documentElement);
    const g = (v) => s.getPropertyValue(v).trim();
    const text = g('--text') || '#f1f5f9';
    return {
        text: g('--chart-text') || '#94a3b8',
        muted: g('--chart-muted') || '#64748b',
        grid: g('--chart-grid') || '#1e293b',
        title: text,
        tooltip: {
            backgroundColor: g('--chart-tooltip-bg') || '#1a2332',
            titleColor: text,
            bodyColor: g('--chart-text') || '#94a3b8',
            borderColor: g('--chart-tooltip-border') || '#334155',
            borderWidth: 1,
            padding: 12,
            cornerRadius: 8,
        },
    };
};

/* ── Sidebar mobile ──────────────────────── */
function initSidebar() {
    const sidebar   = document.getElementById('sidebar');
    const menuBtn   = document.getElementById('menuBtn');
    const toggleBtn = document.getElementById('sidebarToggle');
    const overlay   = document.getElementById('sidebarOverlay');

    if (!sidebar) return;

    const open = () => {
        sidebar.classList.add('open');
        overlay?.classList.add('visible');
        overlay?.setAttribute('aria-hidden', 'false');
        document.body.classList.add('sidebar-open');
    };

    const close = () => {
        sidebar.classList.remove('open');
        overlay?.classList.remove('visible');
        overlay?.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('sidebar-open');
    };

    const toggle = () => {
        if (sidebar.classList.contains('open')) close();
        else open();
    };

    menuBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        toggle();
    });

    toggleBtn?.addEventListener('click', close);
    overlay?.addEventListener('click', close);

    sidebar.querySelectorAll('.nav-item').forEach((link) => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 768) close();
        });
    });

    document.addEventListener('click', (e) => {
        if (window.innerWidth > 768) return;
        if (!sidebar.classList.contains('open')) return;
        if (!sidebar.contains(e.target) && !menuBtn?.contains(e.target)) {
            close();
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) close();
    });
}

/* ── Botão de atualização (chama API REST) ── */
function initRefreshBtn() {
    const btn = document.getElementById('refreshBtn');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        btn.classList.add('spinning');
        btn.disabled = true;

        try {
            const res  = await fetch('/api/v1/atualizar', { method: 'POST' });
            const json = await res.json();

            if (json.status === 'ok') {
                showToast(
                    `✅ ${json.data.candidatos_atualizados} candidatos atualizados!`,
                    'success'
                );
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showToast('Erro ao atualizar dados.', 'error');
            }
        } catch {
            showToast('Erro de conexão ao servidor.', 'error');
        } finally {
            btn.classList.remove('spinning');
            btn.disabled = false;
        }
    });
}

/* ── Flash auto-close após 5s ────────────── */
function initFlashAutoClose() {
    document.querySelectorAll('.flash').forEach(el => {
        setTimeout(() => el.remove(), 5000);
    });
}

/* ── Temas checkboxes (form de candidato) ── */
function initTemaCheckboxes() {
    document.querySelectorAll('.tema-check-item input[type=checkbox]').forEach(cb => {
        const label = cb.nextElementSibling;
        if (!label) return;

        const update = () => {
            if (cb.checked) {
                label.style.fontWeight = '700';
                label.style.opacity    = '1';
            } else {
                label.style.fontWeight = '400';
                label.style.opacity    = '0.6';
            }
        };

        update();
        cb.addEventListener('change', update);
    });
}

/* ── Toast notification ──────────────────── */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className   = `toast ${type} show`;

    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
}

window.showToast = showToast;
