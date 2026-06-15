/** 对话核心逻辑：列表管理、消息发送、SSE 流式接收。 */

let currentConvId = null;
let currentModel = 'deepseek-chat';

/* ─── 初始化 ──────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    const user = requireAuth();
    if (!user) return;
    document.getElementById('current-user').textContent = user.username;
    loadConversations();
    bindEvents();
});

/* ─── 事件绑定 ────────────────────────────────── */
function bindEvents() {
    document.getElementById('btn-new-conv').addEventListener('click', createConversation);
    document.getElementById('btn-logout').addEventListener('click', logout);
    document.getElementById('btn-send').addEventListener('click', sendMessage);
    document.getElementById('send-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    document.getElementById('model-select').addEventListener('change', (e) => {
        currentModel = e.target.value;
    });
}

/* ─── 对话列表 ────────────────────────────────── */
async function loadConversations() {
    try {
        const data = await api.get('/conversations');
        const list = document.getElementById('conv-list');
        list.innerHTML = '';
        if (data.items.length === 0) {
            list.innerHTML = '<div class="empty-list">暂无对话<br>点击「新建对话」开始</div>';
            return;
        }
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

    try {
        const detail = await api.get(`/conversations/${id}`);
        renderMessages(detail.messages);
        // 更新模型选择器
        currentModel = detail.model_name;
        document.getElementById('model-select').value = detail.model_name;
    } catch (err) {
        showToast(err.message);
    }
}

async function createConversation() {
    const title = prompt('对话标题（可选）：', '新对话') || '新对话';
    try {
        const conv = await api.post('/conversations', { title, model_name: currentModel });
        currentConvId = conv.id;
        await loadConversations();
        // 选中新对话
        selectConversation(conv.id);
        // 清空消息区域
        document.getElementById('message-list').innerHTML = `
            <div class="welcome-message">
                <h2>AI 智能对话助手</h2>
                <p>开始你的对话吧！</p>
            </div>
        `;
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
        document.getElementById('message-list').innerHTML = '';
        await loadConversations();
    } catch (err) {
        showToast(err.message);
    }
}

/* ─── 消息渲染 ────────────────────────────────── */
function renderMessages(messages) {
    const container = document.getElementById('message-list');
    container.innerHTML = '';
    messages.forEach(msg => {
        appendMessage(msg.role, msg.content);
    });
    scrollToBottom();
}

function appendMessage(role, content) {
    const container = document.getElementById('message-list');
    const div = document.createElement('div');
    div.className = `message message-${role}`;
    div.innerHTML = `
        <div class="message-bubble">${escapeHtml(content)}</div>
    `;
    container.appendChild(div);
}

function appendStreamingBubble(role) {
    const container = document.getElementById('message-list');
    const div = document.createElement('div');
    div.className = `message message-${role}`;
    div.innerHTML = `<div class="message-bubble streaming"></div>`;
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
    input.disabled = true;
    document.getElementById('btn-send').disabled = true;

    // 显示用户消息
    appendMessage('user', content);
    scrollToBottom();

    // 创建 AI 流式气泡
    const bubble = appendStreamingBubble('assistant');
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
            buffer = lines.pop(); // 保留不完整的行

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
                        } else if (currentEvent === 'done') {
                            // 流正常结束，在循环外处理
                        } else if (currentEvent === 'error') {
                            bubble.textContent = `错误: ${payload.detail || '未知错误'}`;
                            bubble.classList.add('error');
                        }
                    } catch { /* 跳过解析失败 */ }
                }
            }
        }

        if (!accumulated) {
            bubble.textContent = '(AI 未返回内容)';
        }

        bubble.classList.remove('streaming');
        document.getElementById('streaming-bubble').removeAttribute('id');
        await loadConversations();  // 刷新列表，更新最后消息预览

    } catch (err) {
        bubble.textContent = `错误: ${err.message}`;
        bubble.classList.add('error');
        bubble.classList.remove('streaming');
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
