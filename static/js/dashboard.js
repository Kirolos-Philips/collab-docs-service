import API from './api.js';

const els = {
    docList: document.getElementById('doc-list'),
    noDocs: document.getElementById('no-docs'),
    logoutBtn: document.getElementById('logout-btn'),
    newDocBtn: document.getElementById('new-doc-btn'),
    modalOverlay: document.getElementById('modal-overlay'),
    closeModal: document.getElementById('close-modal'),
    confirmCreate: document.getElementById('confirm-create'),
    newDocTitle: document.getElementById('new-doc-title'),
    userProfile: document.getElementById('user-profile'),
    userName: document.getElementById('user-name'),
    userEmail: document.getElementById('user-email'),
    userAvatar: document.getElementById('user-avatar'),
    userProfile: document.getElementById('user-profile'),
    profileModal: document.getElementById('profile-modal'),
    closeProfileModal: document.getElementById('close-profile-modal'),
    settingsAvatarPreview: document.getElementById('settings-avatar-preview'),
    avatarInput: document.getElementById('avatar-input'),
    settingsUsername: document.getElementById('settings-username'),
    settingsEmail: document.getElementById('settings-email'),
    saveProfileBtn: document.getElementById('save-profile')
};

async function loadDocuments() {
    try {
        const docs = await API.get('/documents/');
        renderDocuments(docs);
    } catch (e) {
        console.error('Failed to load documents:', e);
    }
}

function renderDocuments(docs) {
    els.docList.innerHTML = '';

    if (docs.length === 0) {
        els.noDocs.style.display = 'block';
        return;
    }

    els.noDocs.style.display = 'none';
    docs.forEach(doc => {
        const card = document.createElement('div');
        card.className = 'doc-card';
        card.onclick = () => window.location.href = `/static/editor.html?id=${doc.id}`;

        card.innerHTML = `
            <h3 style="margin-bottom: 8px; font-size: 1.1rem;">${doc.title || 'Untitled'}</h3>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px;">
                ${doc.content ? doc.content.substring(0, 60) + '...' : 'No content yet.'}
            </p>
            <div style="margin-top: auto; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 12px;">
                <span style="font-size: 0.75rem; color: var(--text-muted);">
                    Updated ${new Date(doc.updated_at).toLocaleDateString()}
                </span>
                <div style="font-size: 0.7rem; background: #f1f5f9; padding: 2px 8px; border-radius: 4px; font-weight: 600; color: #64748b;">
                    ${doc.collaborators.length + 1} Member(s)
                </div>
            </div>
        `;
        els.docList.appendChild(card);
    });
}

// Event Listeners
els.logoutBtn.onclick = () => API.logout();

els.newDocBtn.onclick = () => {
    els.modalOverlay.style.display = 'flex';
    els.newDocTitle.focus();
};

els.closeModal.onclick = () => {
    els.modalOverlay.style.display = 'none';
};

els.confirmCreate.onclick = async () => {
    const title = els.newDocTitle.value.trim();
    if (!title) return;

    try {
        els.confirmCreate.disabled = true;
        const newDoc = await API.post('/documents/', { title });
        window.location.href = `/static/editor.html?id=${newDoc.id}`;
    } catch (e) {
        alert(e.message);
    } finally {
        els.confirmCreate.disabled = false;
    }
};

async function initUser() {
    try {
        const user = await API.getMe();
        if (user) {
            els.userProfile.style.display = 'flex';
            els.userName.textContent = user.username;
            els.userEmail.textContent = user.email;
            els.userAvatar.src = user.avatar_url;
            els.userAvatar.alt = user.username;

            // Pre-fill settings
            els.settingsUsername.value = user.username;
            els.settingsEmail.value = user.email;
            els.settingsAvatarPreview.src = user.avatar_url;
        }
    } catch (e) {
        console.error('Failed to load user profile:', e);
    }
}

// Profile Management
els.userProfile.onclick = () => {
    els.profileModal.style.display = 'flex';
};

els.closeProfileModal.onclick = () => {
    els.profileModal.style.display = 'none';
};

els.avatarInput.onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            els.settingsAvatarPreview.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
};

els.saveProfileBtn.onclick = async () => {
    try {
        els.saveProfileBtn.disabled = true;

        // 1. Upload Avatar if changed
        if (els.avatarInput.files[0]) {
            await API.uploadAvatar(els.avatarInput.files[0]);
        }

        // 2. Update Username if changed
        const newUsername = els.settingsUsername.value.trim();
        if (newUsername) {
            await API.updateProfile({ username: newUsername });
        }

        await initUser();
        els.profileModal.style.display = 'none';
        els.avatarInput.value = ''; // Reset input
    } catch (e) {
        alert(e.message);
    } finally {
        els.saveProfileBtn.disabled = false;
    }
};

// Initialization
if (!API.isAuthenticated()) {
    window.location.href = '/static/index.html';
} else {
    initUser();
    loadDocuments();
}
