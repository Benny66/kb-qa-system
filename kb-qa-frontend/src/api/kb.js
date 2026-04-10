import request from './request'

/** 获取知识库列表 */
export const listKb = () => request.get('/kb')

/** 上传 TXT 知识库 */
export const uploadKb = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return request.post('/kb/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
}

/** 删除知识库 */
export const deleteKb = (kbId) => request.delete(`/kb/${kbId}`)
