import axios from 'axios'

const API_BASE_URL = 'http://localhost:5000/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const fetchGraphData = async () => {
  try {
    const response = await apiClient.get('/graph')
    return response.data
  } catch (error) {
    console.error('获取图谱数据失败:', error)
    return { nodes: [], edges: [] }
  }
}

export const askQuestion = async (question, topK = 5) => {
  try {
    const response = await apiClient.post('/qa/ask', {
      query: question,
      top_k: topK
    })
    return response.data
  } catch (error) {
    console.error('提问失败:', error)
    return { answer: '抱歉，问答服务暂时不可用', evidence_hits: [] }
  }
}

export const getEntityDetail = async (entityId) => {
  try {
    const response = await apiClient.get(`/entity/${entityId}`)
    return response.data
  } catch (error) {
    console.error('获取实体详情失败:', error)
    return null
  }
}