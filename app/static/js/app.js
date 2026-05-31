/* ========================================
   PESQUISA ELEITORAL 2026 — APP.JS
   JavaScript do lado cliente (Flask MVC)
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initRefreshBtn();
    initFlashAutoClose();
    initTemaCheckboxes();
});

/* ── Sidebar mobile ──────────────────────── */
function initSidebar() {
    const sidebar    = document.getElementById('sidebar');
    const menuBtn    = document.getElementById('menuBtn');
    const toggleBtn  = document.getElementById('sidebarToggle');

    if (!sidebar) return;

    const toggle = () => sidebar.classList.toggle('open');

    menuBtn  ?.addEventListener('click', toggle);
    toggleBtn?.addEventListener('click', toggle);

    // Fechar ao clicar fora no mobile
    document.addEventListener('click', (e) => {
        if (window.innerWidth > 768) return;
        if (!sidebar.contains(e.target) &&
            !menuBtn?.contains(e.target)) {
            sidebar.classList.remove('open');
        }
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
                // Recarregar a página após 1.5s para refletir novos dados
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

/* ── Expõe globalmente para uso inline ────── */
window.showToast = showToast;
