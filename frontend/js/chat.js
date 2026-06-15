/** 对话核心逻辑：列表管理、消息发送、SSE 流式接收。 */

let currentConvId = null;
let currentModel = 'deepseek-chat';

/* ─── 初始化 ──────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
    const user = requireAuth();
    if (!user) return;
    document.getElementById('current-user').textContent = user.username;
    await loadModelList();
    await loadConversations();
    bindEvents();
});

/* ─── 事件绑定 ────────────────────────────────── */
function bindEvents() {
    document.getElementById('btn-new-conv').addEventListener('click', createConversation);
    document.getElementById('btn-logout').addEventListener('click', logout);
    document.getElementById('btn-send').addEventListener('click', sendMessage);
    document.getElementById('btn-delete-conv').addEventListener('click', deleteCurrentConversation);

    const input = document.getElementById('send-input');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    // 自动缩放 textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    document.getElementById('model-select').addEventListener('change', (e) => {
        currentModel = e.target.value;
    });
}

/* ─── 模型列表 ────────────────────────────────── */
async function loadModelList() {
    try {
        const data = await api.get('/models');
        const select = document.getElementById('model-select');
        select.innerHTML = '';
        data.models.forEach(m => {
            const option = document.createElement('option');
            option.value = m.id;
            option.textContent = m.name;
            select.appendChild(option);
        });
        currentModel = data.default;
        select.value = data.default;
    } catch {
        // 降级：使用 HTML 中预设的选项
    }
}

/* ─── 对话列表 ────────────────────────────────── */
async function loadConversations() {
    try {
        const data = await api.get('/conversations');
        const list = document.getElementById('conv-list');
        if (data.items.length === 0) {
            list.innerHTML = '<div class="empty-list">暂无对话<br>点击上方「+ 新建对话」开始</div>';
            return;
        }
        list.innerHTML = '';
        data.items.forEach(conv => {
            const el = document.createElement('div');
            el.className = `conv-item${conv.id === currentConvId ? ' active' : ''}`;
            el.dataset.id = conv.id;
            el.innerHTML = `
                <div class="conv-item-title">${escapeHtml(conv.title)}</div>
                <div class="conv-item-preview">${escapeHtml(conv.last_message || '点击开始对话')}</div>
            `;
            el.addEventListener('click', () => selectConversation(conv.id));
            list.appendChild(el);
        });
    } catch (err) {
        showToast(err.message);
    }
}

async function selectConversation(id) {
    currentConvId = id;
    document.querySelectorAll('.conv-item').forEach(item => {
        item.classList.toggle('active', Number(item.dataset.id) === id);
    });

    // 显示加载状态
    document.getElementById('message-list').innerHTML = '<div class="loading-state"><span class="spinner"></span><p>加载消息中...</p></div>';

    try {
        const detail = await api.get(`/conversations/${id}`);
        currentModel = detail.model_name;
        document.getElementById('model-select').value = detail.model_name;
        renderMessages(detail.messages);
    } catch (err) {
        showToast(err.message);
        document.getElementById('message-list').innerHTML = '<div class="welcome-message"><p>加载失败，请重试</p></div>';
    }
}

async function createConversation() {
    try {
        // 直接用默认标题创建，不用 prompt
        const conv = await api.post('/conversations', { title: '新对话', model_name: currentModel });
        currentConvId = conv.id;
        await loadConversations();
        // 清空消息区域
        document.getElementById('message-list').innerHTML = `
            <div class="welcome-message">
                <h2>AI 智能对话助手</h2>
                <p>开始你的对话吧！</p>
            </div>
        `;
        document.getElementById('send-input').focus();
    } catch (err) {
        showToast(err.message);
    }
}

async function deleteCurrentConversation() {
    if (!currentConvId) return;
    if (!confirm('确定删除此对话？所有消息将被删除。')) return;
    try {
        await api.delete(`/conversations/${currentConvId}`);
        currentConvId = null;
        document.getElementById('message-list').innerHTML = `
            <div class="welcome-message">
                <h2>AI 智能对话助手</h2>
                <p>在左侧创建新对话，开始与 AI 交流</p>
            </div>
        `;
        await loadConversations();
    } catch (err) {
        showToast(err.message);
    }
}

/* ─── 消息渲染 ────────────────────────────────── */
function renderMessages(messages) {
    const container = document.getElementById('message-list');
    container.innerHTML = '';
    if (messages.length === 0) {
        container.innerHTML = '<div class="welcome-message"><h2>AI 智能对话助手</h2><p>开始你的对话吧！</p></div>';
        return;
    }
    messages.forEach(msg => appendMessage(msg.role, msg.content));
    scrollToBottom();
}

function appendMessage(role, content) {
    const container = document.getElementById('message-list');
    const div = document.createElement('div');
    div.className = `message message-${role}`;
    div.innerHTML = `<div class="message-bubble">${escapeHtml(content)}</div>`;
    container.appendChild(div);
}

function appendStreamingBubble() {
    const container = document.getElementById('message-list');
    const div = document.createElement('div');
    div.className = 'message message-assistant';
    div.innerHTML = '<div class="message-bubble streaming"></div>';
    div.id = 'streaming-bubble';
    container.appendChild(div);
    return div.querySelector('.streaming');
}

/* ─── SSE 流式发送消息 ─────────────────────────── */
async function sendMessage() {
    const input = document.getElementById('send-input');
    const content = input.value.trim();
    if (!content) return;
    if (!currentConvId) {
        showToast('请先创建一个对话');
        return;
    }

    input.value = '';
    input.style.height = 'auto';
    input.disabled = true;
    document.getElementById('btn-send').disabled = true;

    // 显示用户消息
    appendMessage('user', content);
    scrollToBottom();

    // 创建 AI 流式气泡
    const bubble = appendStreamingBubble();
    let accumulated = '';

    try {
        const response = await fetch(`http://localhost:8000/api/conversations/${currentConvId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`,
            },
            body: JSON.stringify({ content }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || '发送失败');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentEvent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.slice(7).trim();
                    continue;
                }

                if (line.startsWith('data: ')) {
                    try {
                        const payload = JSON.parse(line.slice(6));
                        if (currentEvent === 'delta') {
                            accumulated += payload.content || '';
                            bubble.textContent = accumulated;
                            scrollToBottom();
                        } else if (currentEvent === 'error') {
                            bubble.textContent = '错误: ' + (payload.detail || '未知错误');
                            bubble.classList.add('error');
                        }
                        // done 事件忽略，在流结束后统一处理
                    } catch { /* 跳过解析失败 */ }
                }
            }
        }

        if (!accumulated) {
            bubble.textContent = '(AI 未返回内容)';
        }

        bubble.classList.remove('streaming');
        document.getElementById('streaming-bubble').removeAttribute('id');
        await loadConversations();  // 刷新列表预览

    } catch (err) {
        bubble.textContent = '错误: ' + err.message;
        bubble.classList.add('error');
        bubble.classList.remove('streaming');
        document.getElementById('streaming-bubble').removeAttribute('id');
    } finally {
        input.disabled = false;
        document.getElementById('btn-send').disabled = false;
        input.focus();
    }
}

/* ─── 辅助函数 ────────────────────────────────── */
function scrollToBottom() {
    const container = document.getElementById('message-list');
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
