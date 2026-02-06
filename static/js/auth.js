import API from './api.js';

const els = {
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    verifyForm: document.getElementById('verify-form'),
    showRegister: document.getElementById('show-register'),
    showLogin: document.getElementById('show-login'),
    msg: document.getElementById('message'),
    subtitle: document.getElementById('auth-subtitle'),

    loginBtn: document.getElementById('login-btn'),
    registerBtn: document.getElementById('register-btn'),
    verifyBtn: document.getElementById('verify-btn'),

    loginEmail: document.getElementById('login-email'),
    loginPass: document.getElementById('login-password'),
    regUser: document.getElementById('reg-username'),
    regEmail: document.getElementById('reg-email'),
    regPass: document.getElementById('reg-password'),
    verifyOtp: document.getElementById('verify-otp')
};

function showMsg(text, type = 'success') {
    els.msg.textContent = text;
    els.msg.style.display = 'block';
    els.msg.style.backgroundColor = type === 'success' ? '#dcfce7' : '#fee2e2';
    els.msg.style.color = type === 'success' ? '#166534' : '#991b1b';
}

function switchForm(form) {
    els.loginForm.style.display = form === 'login' ? 'block' : 'none';
    els.registerForm.style.display = form === 'register' ? 'block' : 'none';
    els.verifyForm.style.display = form === 'verify' ? 'block' : 'none';

    if (form === 'login') els.subtitle.textContent = 'Welcome back.';
    if (form === 'register') els.subtitle.textContent = 'Join the collaboration.';
    if (form === 'verify') els.subtitle.textContent = 'One last step.';
}

// Event Listeners
els.showRegister.onclick = (e) => { e.preventDefault(); switchForm('register'); };
els.showLogin.onclick = (e) => { e.preventDefault(); switchForm('login'); };

els.loginBtn.onclick = async () => {
    try {
        els.loginBtn.disabled = true;
        await API.login(els.loginEmail.value, els.loginPass.value);
        window.location.href = '/static/dashboard.html';
    } catch (e) {
        showMsg(e.message, 'error');
    } finally {
        els.loginBtn.disabled = false;
    }
};

els.registerBtn.onclick = async () => {
    try {
        els.registerBtn.disabled = true;
        await fetch('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: els.regUser.value,
                email: els.regEmail.value,
                password: els.regPass.value
            })
        });
        showMsg('OTP sent to your email.');
        switchForm('verify');
    } catch (e) {
        showMsg(e.message, 'error');
    } finally {
        els.registerBtn.disabled = false;
    }
};

els.verifyBtn.onclick = async () => {
    try {
        els.verifyBtn.disabled = true;
        const res = await fetch('/auth/verify-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: els.regEmail.value,
                otp: els.verifyOtp.value
            })
        });
        if (!res.ok) throw new Error('Verification failed');

        showMsg('Verified! Logging in...');
        // Auto-login after verification
        await API.login(els.regEmail.value, els.regPass.value);
        window.location.href = '/static/dashboard.html';
    } catch (e) {
        showMsg(e.message, 'error');
    } finally {
        els.verifyBtn.disabled = false;
    }
};

// Check if already logged in
if (API.isAuthenticated()) {
    window.location.href = '/static/dashboard.html';
}
