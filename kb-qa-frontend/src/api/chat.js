import request from './request'

/** AI 问答 */
export const sendChat = (kbId, question) =>
  request.post('/chat', { kb_id: kbId, question })

/** 获取问答历史 */
export const getHistory = (params = {}) =>
  request.get('/chat/history', { params })

/** 删除单条历史 */
export const deleteHistory = (id) => request.delete(`/chat/history/${id}`)
