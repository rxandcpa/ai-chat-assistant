/** 认证相关：登录、注册、Token 管理、页面守卫。 */

/** 显示 Toast 消息 */
function showToast(message, type = 'error') {
    const container = document.querySelector('.toast-container') || (() => {
        const el = document.createElement('div');
        el.className = 'toast-container';
        document.body.appendChild(el);
        return el;
    })();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 3500);
}

/** 表单提交封装 */
function handleForm(formId, apiCall, redirectUrl) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        const btnText = btn.textContent;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span>';

        // 清空错误提示
        form.querySelectorAll('.form-error').forEach(el => { el.style.display = 'none'; el.textContent = ''; });

        try {
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            const result = await apiCall(data);

            if (result.access_token) {
                localStorage.setItem('access_token', result.access_token);
                localStorage.setItem('user', JSON.stringify(result.user));
            }
            window.location.href = redirectUrl;
        } catch (err) {
            showToast(err.message, 'error');
            btn.disabled = false;
            btn.textContent = btnText;
        }
    });
}

/** 页面守卫：未登录时跳转到登录页 */
function requireAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login.html';
        return null;
    }
    try {
        return JSON.parse(localStorage.getItem('user'));
    } catch {
        return null;
    }
}

/** 登出 */
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login.html';
}
