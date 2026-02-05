document.addEventListener('DOMContentLoaded', () => {
    // Modal Logic
    const modal = document.getElementById('userModal');
    const openBtn = document.getElementById('newUserBtn');
    const closeBtn = document.querySelector('.close-btn');

    if (openBtn) {
        openBtn.addEventListener('click', () => {
            modal.classList.add('active');
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
        });
    }

    // Profile Modal Logic
    const profileModal = document.getElementById('profileModal');
    const profileBtn = document.getElementById('profileBtn');
    const profileCloseBtn = document.querySelector('.close-btn-profile');

    if (profileBtn) {
        profileBtn.addEventListener('click', () => {
            profileModal.classList.add('active');
        });
    }

    if (profileCloseBtn) {
        profileCloseBtn.addEventListener('click', () => {
            profileModal.classList.remove('active');
        });
    }

    // Old window listener removed, moved to bottom to handle all modals
    /*
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
        if (e.target === profileModal) {
            profileModal.classList.remove('active');
        }
    });
    */

    // Auto Logout - 10 Minutos
    (function () {
        let timeout;
        const LIMIT = 10 * 60 * 1000; // 10 min

        function resetTimer() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                window.location.href = '/logout';
            }, LIMIT);
        }

        window.onload = resetTimer;
        document.onmousemove = resetTimer;
        document.onkeypress = resetTimer;
        document.onclick = resetTimer;
        document.onscroll = resetTimer;
    })();
});

function confirmDelete(usuario) {
    if (confirm(`¿Estás seguro de que quieres eliminar al usuario '${usuario}'?`)) {
        // Enviar form post oculto
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/admin/usuarios/eliminar';

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'usuario';
        input.value = usuario;

        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    }
}

function openChangePassModal(usuario) {
    const modal = document.getElementById('changePassModal');
    const inputUser = document.getElementById('changePassUser');
    const lblUser = document.getElementById('lblChangeUser');
    const closeBtn = document.querySelector('.close-btn-pass');

    inputUser.value = usuario;
    lblUser.innerText = usuario;

    modal.classList.add('active');

    if (closeBtn) {
        closeBtn.onclick = () => {
            modal.classList.remove('active');
        }
    }

    // Close on click outside (handling added to window listener in main check)
    // But we need to add specific ID check to the main window listener or just add a specific one here.
    // Reusing the global window click listener is better if we update it.
}

// Update window click listener to include new modal
window.addEventListener('click', (e) => {
    const m1 = document.getElementById('userModal');
    const m2 = document.getElementById('profileModal');
    const m3 = document.getElementById('changePassModal'); // New one

    if (e.target === m1) m1.classList.remove('active');
    if (e.target === m2) m2.classList.remove('active');
    if (e.target === m3) m3.classList.remove('active');
});
