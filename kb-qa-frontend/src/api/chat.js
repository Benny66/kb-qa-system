import request from './request'

/** AI 问答（阻塞式） */
export const sendChat = (kbId, question, options = {}) =>
  request.post('/chat', {
    kb_id: kbId,
    question,
    session_id: options.sessionId || undefined,
    history: options.history || [],
  })

/** 获取问答历史 */
export const getHistory = (params = {}) =>
  request.get('/chat/history', { params })

/** 删除单条历史 */
export const deleteHistory = (id) => request.delete(`/chat/history/${id}`)

/** 获取会话列表 */
export const getChatSessions = (params = {}) =>
  request.get('/chat/sessions', { params })

/** 创建会话 */
export const createChatSession = (kbId, title = '') =>
  request.post('/chat/sessions', { kb_id: kbId, title })

/** 获取会话详情 */
export const getChatSessionDetail = (sessionId) =>
  request.get(`/chat/sessions/${sessionId}`)

/** 删除会话 */
export const deleteChatSession = (sessionId) =>
  request.delete(`/chat/sessions/${sessionId}`)

/**
 * AI 问答（SSE 流式，任务 3.1）
 *
 * @param {number} kbId - 知识库 ID
 * @param {string} question - 用户问题
 * @param {object} options - { sessionId, history }
 * @param {object} callbacks - { onDelta(content), onDone(data), onError(error) }
 * @returns {AbortController} 可用于中止请求（任务 3.3）
 */
export function sendChatStream(kbId, question, options = {}, callbacks = {}) {
  const controller = new AbortController()

  // 使用原生 fetch，自动注入 JWT Token（任务 3.2）
  const token = localStorage.getItem('token')
  const baseURL = import.meta.env.VITE_API_BASE_URL || ''

  fetch(`${baseURL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      kb_id: kbId,
      question,
      session_id: options.sessionId || undefined,
      history: options.history || [],
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        // 非 2xx 状态码，尝试解析错误信息
        const errData = await response.json().catch(() => ({}))
        const errMsg = errData.msg || `请求失败（${response.status}）`
        callbacks.onError?.(errMsg)
        return
      }

      // 使用 ReadableStream 逐行解析 SSE（任务 3.4）
      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        // 保留未完整的最后一行
        buffer = lines.pop()

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data:')) continue

          const jsonStr = trimmed.slice('data:'.length).trim()
          if (!jsonStr) continue

          try {
            const frame = JSON.parse(jsonStr)
            // 根据 type 分发回调（任务 3.5）
            if (frame.type === 'delta') {
              callbacks.onDelta?.(frame.content)
            } else if (frame.type === 'done') {
              callbacks.onDone?.(frame)
            } else if (frame.type === 'error') {
              callbacks.onError?.(frame.error)
            }
          } catch {
            // 忽略无法解析的行
          }
        }
      }
    })
    .catch((err) => {
      if (err.name === 'AbortError') return // 用户主动中止，不触发错误
      callbacks.onError?.(err.message || '流式请求失败')
    })

  return controller
}
