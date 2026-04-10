import request from './request'

/** 登录 */
export const login = (username, password) =>
  request.post('/auth/login', { username, password })

/** 获取当前用户信息 */
export const getMe = () => request.get('/auth/me')
