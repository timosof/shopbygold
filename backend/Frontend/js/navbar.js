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
        // LOGGED IN
        if (usernameEl) { usernameEl.textContent = 'Hi, ' + user.username; usernameEl.classList.remove('hidden'); }
        if (mUsername) { mUsername.textContent = 'Hi, ' + user.username; mUsername.classList.remove('hidden'); }
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
    } else {
        // LOGGED OUT
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

async function updateCartCount() {
    const token = localStorage.getItem('token');
    const el = document.getElementById('cart-count');
    if (!el) return;
    if (!token) { el.textContent = '0'; return; }
    try {
        const res = await fetch('/api/cart', { headers: { 'Authorization': 'Bearer ' + token } });
        if (!res.ok) { el.textContent = '0'; return; }
        const data = await res.json();
        const items = data.items || data.cart?.items || [];
        el.textContent = items.reduce((s,i)=>s+(i.quantity||0),0);
    } catch { el.textContent = '0'; }
}

async function addToCart(productId) {
    const token = localStorage.getItem('token');
    if (!token) { alert('Please login first'); location.href='login.html'; return; }
    const res = await fetch(API_BASE + '/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer '+token },
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
        searchInput.addEventListener('keypress', (e)=>{
            if(e.key==='Enter'){ const q=e.target.value.trim(); location.href = q ? 'shop.html?search='+encodeURIComponent(q) : 'shop.html'; }
        });
    }
});