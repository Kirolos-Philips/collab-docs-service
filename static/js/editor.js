import API from './api.js';
import * as Y from 'yjs';
import { Awareness } from 'y-protocols/awareness';

const els = {
    title: document.getElementById('doc-title'),
    textarea: document.getElementById('editor-textarea'),
    presenceBar: document.getElementById('presence-bar'),
    syncStatus: document.getElementById('sync-status'),
    syncText: document.getElementById('sync-text'),
    cursorsLayer: document.getElementById('cursors-layer'),
    shareBtn: document.getElementById('share-btn'),
    shareModal: document.getElementById('share-modal'),
    closeShareModal: document.getElementById('close-share-modal'),
    collabList: document.getElementById('collaborators-list'),
    inviteEmail: document.getElementById('invite-email'),
    inviteRole: document.getElementById('invite-role'),
    addCollabBtn: document.getElementById('add-collab-btn'),
    userAvatar: document.getElementById('user-avatar'),
    userName: document.getElementById('user-name'),
    userEmail: document.getElementById('user-email'),
    userProfile: document.getElementById('user-profile'),
    profileModal: document.getElementById('profile-modal'),
    closeProfileModal: document.getElementById('close-profile-modal'),
    settingsAvatarPreview: document.getElementById('settings-avatar-preview'),
    avatarInput: document.getElementById('avatar-input'),
    settingsUsername: document.getElementById('settings-username'),
    settingsEmail: document.getElementById('settings-email'),
    saveProfileBtn: document.getElementById('save-profile')
};

const urlParams = new URL(window.location.href).searchParams;
const docId = urlParams.get('id');

if (!docId || !API.isAuthenticated()) {
    window.location.href = '/static/dashboard.html';
}

// Yjs & Awareness Setup
const ydoc = new Y.Doc();
const ytext = ydoc.getText('content');
const awareness = new Awareness(ydoc);

let ws = null;
let reconnectAttempts = 0;

function connect() {
    if (ws) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const token = localStorage.getItem('access_token');
    const url = `${protocol}//${window.location.host}/documents/${docId}/sync?token=${token}`;

    ws = new WebSocket(url);

    ws.onopen = () => {
        reconnectAttempts = 0;
        updateStatus('connected');
        // Profile info will be updated in initUser()
        awareness.setLocalStateField('user', {
            name: 'Loading...',
            color: '#2563eb',
            avatar: ''
        });
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === 'sync_state') {
            const state = Uint8Array.from(atob(message.state), c => c.charCodeAt(0));
            Y.applyUpdate(ydoc, state, 'socket');
        } else if (message.type === 'update') {
            const update = Uint8Array.from(atob(message.update), c => c.charCodeAt(0));
            Y.applyUpdate(ydoc, update, 'socket');
        } else if (message.type === 'presence') {
            handlePresence(message);
        }
    };

    ws.onclose = () => {
        ws = null;
        updateStatus('disconnected');
        if (reconnectAttempts < 5) {
            reconnectAttempts++;
            setTimeout(connect, 2000 * reconnectAttempts);
        }
    };

    ws.onerror = () => ws.close();
}

function updateStatus(state) {
    if (state === 'connected') {
        els.syncStatus.style.backgroundColor = 'var(--success)';
        els.syncText.textContent = 'Synced';
    } else {
        els.syncStatus.style.backgroundColor = 'var(--error)';
        els.syncText.textContent = 'Offline (Retrying...)';
    }
}

// Logic: Observe Yjs changes and relay them
ydoc.on('update', (update, origin) => {
    if (origin !== 'socket' && ws && ws.readyState === WebSocket.OPEN) {
        const updateB64 = btoa(String.fromCharCode(...update));
        ws.send(JSON.stringify({ type: 'update', update: updateB64 }));
    }
});

// Sync textarea with Yjs
ytext.observe(() => {
    const currentVal = els.textarea.value;
    const newVal = ytext.toString();
    if (currentVal !== newVal) {
        els.textarea.value = newVal;
    }
});

els.textarea.oninput = (e) => {
    const currentText = ytext.toString();
    const newText = els.textarea.value;

    // Simple naive sync (replace all)
    // For production, use y-textarea or proper diffing
    ydoc.transact(() => {
        ytext.delete(0, currentText.length);
        ytext.insert(0, newText);
    });

    // Broadcast cursor position via presence
    broadcastPresence();
};

function broadcastPresence() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(JSON.stringify({
        type: 'presence',
        cursor: els.textarea.selectionStart
    }));
}

// Presence & Avatars
const activeUsers = new Map();

function handlePresence(data) {
    activeUsers.set(data.user_id, {
        username: data.username,
        avatar_url: data.avatar_url,
        color: data.color,
        cursor: data.cursor,
        lastSeen: Date.now()
    });

    renderPresence();
}

function renderPresence() {
    els.presenceBar.innerHTML = '';
    const now = Date.now();

    activeUsers.forEach((user, id) => {
        // Timeout old presence (5 seconds)
        if (now - user.lastSeen > 5000) {
            activeUsers.delete(id);
            return;
        }

        const img = document.createElement('img');
        img.src = user.avatar_url;
        img.className = 'avatar';
        img.title = user.username;
        img.style.borderColor = user.color;
        els.presenceBar.appendChild(img);
    });

    // Note: Remote Cursors require specific text index to pixel coord mapping.
    // In a simple textarea, we can only show "editing" status or approximate lines.
    // For this lab, we'll focus on the avatars and the backend relay check.
}

// Initial Sync
async function init() {
    try {
        const doc = await API.get(`/documents/${docId}`);
        els.title.textContent = doc.title;
        connect();
        initUser();
    } catch (e) {
        alert('Document not found or access denied');
        window.location.href = '/static/dashboard.html';
    }
}

async function initUser() {
    try {
        const user = await API.getMe();
        if (user) {
            // Update UI
            els.userName.textContent = user.username;
            els.userEmail.textContent = user.email;
            els.userAvatar.src = user.avatar_url;
            els.userAvatar.alt = user.username;

            // Pre-fill settings
            els.settingsUsername.value = user.username;
            els.settingsEmail.value = user.email;
            els.settingsAvatarPreview.src = user.avatar_url;

            // Update Awareness
            awareness.setLocalStateField('user', {
                name: user.username,
                color: user.color || '#2563eb',
                avatar: user.avatar_url
            });
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

init();

// Simple heartbeat for presence
setInterval(() => {
    broadcastPresence();
    renderPresence(); // Cleanup old users
}, 3000);

// Share Modal Logic
els.shareBtn.onclick = () => {
    els.shareModal.style.display = 'flex';
    refreshCollaborators();
};

els.closeShareModal.onclick = () => {
    els.shareModal.style.display = 'none';
};

async function refreshCollaborators() {
    try {
        const doc = await API.get(`/documents/${docId}`);
        renderCollaborators(doc);
    } catch (e) {
        console.error('Failed to fetch collaborators:', e);
    }
}

function renderCollaborators(doc) {
    els.collabList.innerHTML = '';

    // Add Owner
    const ownerDiv = document.createElement('div');
    ownerDiv.style.display = 'flex';
    ownerDiv.style.alignItems = 'center';
    ownerDiv.style.gap = '12px';
    ownerDiv.style.marginBottom = '12px';
    ownerDiv.innerHTML = `
        <div style="width: 32px; height: 32px; border-radius: 50%; background: #e2e8f0; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 800; color: #64748b;">OW</div>
        <div style="flex: 1;">
            <div style="font-size: 0.9rem; font-weight: 600;">Document Owner</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${doc.owner_id === localStorage.getItem('user_id') ? '(You)' : ''}</div>
        </div>
        <div style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted); background: #f1f5f9; padding: 2px 8px; border-radius: 4px;">Owner</div>
    `;
    els.collabList.appendChild(ownerDiv);

    // Add Collaborators
    doc.collaborators.forEach(collab => {
        const div = document.createElement('div');
        div.style.display = 'flex';
        div.style.alignItems = 'center';
        div.style.gap = '12px';
        div.style.marginBottom = '12px';

        const isMe = collab.user_id === localStorage.getItem('user_id');

        div.innerHTML = `
            <img src="${collab.avatar_url}" style="width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--border);">
            <div style="flex: 1;">
                <div style="font-size: 0.9rem; font-weight: 600;">${collab.username} ${isMe ? '(You)' : ''}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${collab.email}</div>
            </div>
            <div style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted); background: #f1f5f9; padding: 2px 8px; border-radius: 4px; text-transform: capitalize;">${collab.role}</div>
            ${doc.owner_id === localStorage.getItem('user_id') ? `
                <button class="btn btn-outline" style="padding: 4px 8px; font-size: 0.7rem; color: var(--error);" onclick="removeCollab('${collab.user_id}')">Remove</button>
            ` : ''}
        `;
        els.collabList.appendChild(div);
    });
}

window.removeCollab = async (userId) => {
    if (!confirm('Remove this collaborator?')) return;
    try {
        await API.request(`/documents/${docId}/collaborators/${userId}`, { method: 'DELETE' });
        refreshCollaborators();
    } catch (e) {
        alert(e.message);
    }
};

els.addCollabBtn.onclick = async () => {
    const email = els.inviteEmail.value.trim();
    const role = els.inviteRole.value;
    if (!email) return;

    try {
        els.addCollabBtn.disabled = true;
        await API.post(`/documents/${docId}/collaborators`, { email, role });
        els.inviteEmail.value = '';
        refreshCollaborators();
    } catch (e) {
        alert(e.message);
    } finally {
        els.addCollabBtn.disabled = false;
    }
};
