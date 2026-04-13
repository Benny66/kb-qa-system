import request from './request'
  
/** AI 问答 */
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
