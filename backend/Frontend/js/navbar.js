// js/navbar.js - Nav + Cart + Auth Roles - FINAL FIXED
const API_BASE = '/api';

function checkAuth() {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || 'null');

    const usernameEl = document.getElementById('username');
    const logoutBtn = document.getElementById('logoutBtn');
    const loginLink = document.getElementById('loginLink');
    const registerLink = document.getElementById('registerLink');
    const adminLink = document.getElementById('adminLink');
    const ordersLink = document.getElementById('ordersLink');

    const mUsername = document.getElementById('m-username');
    const mLogout = document.getElementById('m-logoutBtn');
    const mLogin = document.getElementById('m-loginLink');
    const mRegister = document.getElementById('m-registerLink');
    const mAdmin = document.getElementById('m-adminLink');
    const mOrders = document.getElementById('m-ordersLink');

    if (token && user) {
        const avatarUrl = user.avatar;

        if (usernameEl) {
            if (avatarUrl) {
                usernameEl.innerHTML = `<a href="profile.html"><img src="${avatarUrl}" style="width:32px;height:32px;min-width:32px;min-height:32px" class="rounded-full object-cover border-2 border-yellow-500"></a>`;
            } else {
                usernameEl.innerHTML = `<a href="profile.html" class="font-semibold">Hi, ${user.username}</a>`;
            }
            usernameEl.classList.remove('hidden');
        }
        if (mUsername) {
            if (avatarUrl) {
                mUsername.innerHTML = `<a href="profile.html" class="flex items-center gap-2"><img src="${avatarUrl}" style="width:32px;height:32px;min-width:32px;min-height:32px" class="rounded-full object-cover border-2 border-yellow-500"><span>${user.username}</span></a>`;
            } else {
                mUsername.innerHTML = `<a href="profile.html">Hi, ${user.username}</a>`;
            }
            mUsername.classList.remove('hidden');
        }

        if (logoutBtn) logoutBtn.classList.remove('hidden');
        if (mLogout) mLogout.classList.remove('hidden');
        if (ordersLink) ordersLink.classList.remove('hidden');
        if (mOrders) mOrders.classList.remove('hidden');
        if (loginLink) loginLink.classList.add('hidden');
        if (registerLink) registerLink.classList.add('hidden');
        if (mLogin) mLogin.classList.add('hidden');
        if (mRegister) mRegister.classList.add('hidden');

        if (user.role === 'admin' || user.is_admin === true) {
            if (adminLink) adminLink.classList.remove('hidden');
            if (mAdmin) mAdmin.classList.remove('hidden');
        } else {
            if (adminLink) adminLink.classList.add('hidden');
            if (mAdmin) mAdmin.classList.add('hidden');
        }

        // FETCH FRESH AVATAR FROM API - THIS IS THE PART YOU ASKED ABOUT
        fetch('/api/auth/me', { headers: { 'Authorization': 'Bearer ' + token } })
            .then(r => r.json())
            .then(u => {
                if (u.avatar) {
                    localStorage.setItem('user', JSON.stringify(u));
                    if (usernameEl) usernameEl.innerHTML = `<a href="profile.html"><img src="${u.avatar}" style="width:32px;height:32px;min-width:32px;min-height:32px" class="rounded-full object-cover border-2 border-yellow-500"></a>`;
                    if (mUsername) mUsername.innerHTML = `<a href="profile.html" class="flex items-center gap-2"><img src="${u.avatar}" style="width:32px;height:32px;min-width:32px;min-height:32px" class="rounded-full object-cover border-2 border-yellow-500"><span>${u.username}</span></a>`;
                }
            }).catch(() => {});

    } else {
        if (usernameEl) usernameEl.classList.add('hidden');
        if (mUsername) mUsername.classList.add('hidden');
        if (logoutBtn) logoutBtn.classList.add('hidden');
        if (mLogout) mLogout.classList.add('hidden');
        if (adminLink) adminLink.classList.add('hidden');
        if (mAdmin) mAdmin.classList.add('hidden');
        if (ordersLink) ordersLink.classList.add('hidden');
        if (mOrders) mOrders.classList.add('hidden');
        if (loginLink) loginLink.classList.remove('hidden');
        if (registerLink) registerLink.classList.remove('hidden');
        if (mLogin) mLogin.classList.remove('hidden');
        if (mRegister) mRegister.classList.remove('hidden');
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('cart');
    window.location.href = 'login.html';
}

// async function updateCartCount() {
//     const token = localStorage.getItem('token');
//     const el = document.getElementById('cart-count');
//     if (!el) return;
//     if (!token) { el.textContent = '0'; return; }
//     try {
//         const res = await fetch('/api/cart', { headers: { 'Authorization': 'Bearer ' + token } });
//         if (!res.ok) { el.textContent = '0'; return; }
//         const data = await res.json();
//         const items = data.items || data.cart?.items || [];
//         el.textContent = items.reduce((s, i) => s + (i.quantity || 0), 0);
//     } catch { el.textContent = '0'; }
// }

async function updateCartCount() {
    const token = localStorage.getItem('token');
    const el = document.getElementById('cart-count');
    const btmEl = document.getElementById('btm-cart-count');
    if (!el && !btmEl) return;
    if (!token) { if(el) el.textContent = '0'; if(btmEl) { btmEl.textContent='0'; btmEl.style.display='none'; } return; }
    try {
        const res = await fetch('/api/cart', { headers: { 'Authorization': 'Bearer ' + token } });
        if (!res.ok) { if(el) el.textContent = '0'; if(btmEl) btmEl.style.display='none'; return; }
        const data = await res.json();
        const items = data.items || data.cart?.items || [];
        const count = items.reduce((s, i) => s + (i.quantity || 0), 0);
        if(el) el.textContent = count;
        if(btmEl) { btmEl.textContent = count; btmEl.style.display = count>0 ? 'flex' : 'none'; }
    } catch { if(el) el.textContent = '0'; if(btmEl) btmEl.style.display='none'; }
}

async function addToCart(productId) {
    const token = localStorage.getItem('token');
    if (!token) { alert('Please login first'); location.href = 'login.html'; return; }
    const res = await fetch(API_BASE + '/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ product_id: productId, quantity: 1 })
    });
    if (res.ok) { updateCartCount(); alert('Added to cart'); }
}

document.addEventListener('DOMContentLoaded', function () {
    checkAuth();
    updateCartCount();
    // search handling - uses existing input in HTML
    const searchInput = document.getElementById('nav-search-input');
    if (searchInput) {
        const params = new URLSearchParams(location.search);
        if (params.get('search')) searchInput.value = params.get('search');
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') { const q = e.target.value.trim(); location.href = q ? 'shop.html?search=' + encodeURIComponent(q) : 'shop.html'; }
        });
    }

        // highlight bottom nav active
    const path = window.location.pathname;
    document.querySelectorAll('#bottom-nav a').forEach(a=>{
        const href = a.getAttribute('href');
        if(href && path.includes(href.replace('.html',''))){
            a.classList.add('active');
        }
        // special: shop.html = Home + Shop both active
        if(path.includes('shop.html') && (href==='shop.html')){
            a.classList.add('active');
        }
    });
});

