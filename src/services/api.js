// src/services/api.js
import axios from 'axios'

const API_BASE_URL = 'http://localhost:5000/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加日志
apiClient.interceptors.request.use(
  config => {
    console.log(`📤 发送请求: ${config.method.toUpperCase()} ${config.url}`, config.data || '')
    return config
  },
  error => {
    console.error('❌ 请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器 - 添加日志
apiClient.interceptors.response.use(
  response => {
    console.log(`📥 收到响应: ${response.status}`, response.data)
    return response
  },
  error => {
    console.error('❌ 响应错误:', error)
    return Promise.reject(error)
  }
)

// 获取图谱数据
export const fetchGraphData = async () => {
  try {
    console.log('📢 开始获取图谱数据...')
    const response = await apiClient.get('/graph')
    console.log('✅ 图谱数据获取成功:', response.data)
    return response.data
  } catch (error) {
    console.error('❌ 获取图谱数据失败:', error)
    
    // 返回模拟数据作为后备
    console.log('🔄 使用模拟数据作为后备')
    return {
      nodes: [
        { id: 300, name: '关向应', labels: ['红色人物'], props: { 出生时间: '1902年', 逝世时间: '1946年', 籍贯: '大连金州' } },
        { id: 301, name: '金伯阳', labels: ['红色人物'], props: { 出生时间: '1907年', 逝世时间: '1933年', 籍贯: '大连旅顺' } },
        { id: 200, name: '关向应故居纪念馆', labels: ['红色场馆'], props: { 地址: '金州区向应街道', 开放时间: '9:00-16:30' } },
        { id: 201, name: '大连中华工学会旧址', labels: ['红色场馆'], props: { 地址: '沙河口区黄河路658号' } },
        { id: 202, name: '旅顺万忠墓纪念馆', labels: ['红色场馆'], props: { 地址: '旅顺口区九三路23号' } },
        { id: 400, name: '大连四二七大罢工', labels: ['历史事件'], props: { 发生时间: '1926年', 参与人数: '3万余人' } },
        { id: 500, name: '关向应的钢笔', labels: ['红色展品'], props: { 材质: '黑色金属', 保护级别: '国家三级文物' } },
        { id: 0, name: '1902年', labels: ['时间'], props: {} },
        { id: 101, name: '金州区', labels: ['地点'], props: {} }
      ],
      edges: [
        { source: 300, target: 0, type: '出生时间' },
        { source: 300, target: 101, type: '籍贯' },
        { source: 300, target: 200, type: '相关场馆' },
        { source: 300, target: 500, type: '相关展品' },
        { source: 300, target: 400, type: '领导事件' },
        { source: 200, target: 101, type: '位于' }
      ]
    }
  }
}

// 提问（支持上下文）
export const askQuestion = async (question, topK = 5, context = null) => {
  try {
    console.log('📢 发送问题:', question)
    console.log('📚 上下文:', context)
    
    const response = await apiClient.post('/qa/ask', {
      query: question,
      top_k: topK,
      context: context
    })
    
    console.log('✅ 收到回答:', response.data)
    return response.data
  } catch (error) {
    console.error('❌ 提问失败:', error)
    
    // 简单的本地问答模拟
    return simulateLocalQA(question, context)
  }
}

// 本地模拟问答（当后端不可用时）
const simulateLocalQA = (question, context) => {
  console.log('🔄 使用本地模拟问答')
  
  const knowledge = {
    '关向应': {
      answer: '关向应（1902-1946），大连金州人，中国共产党早期军事领导人，红二方面军总政治委员。1924年入党，曾参与南昌起义和长征。',
      entities: [{ id: 300, name: '关向应', type: '红色人物' }]
    },
    '关向应故居纪念馆': {
      answer: '关向应故居纪念馆位于大连市金州区向应街道关家村1号，开放时间9:00-16:30（周一闭馆），联系电话0411-66661902。',
      entities: [{ id: 200, name: '关向应故居纪念馆', type: '红色场馆' }]
    },
    '纪念馆在哪里': {
      answer: '关向应故居纪念馆位于大连市金州区向应街道关家村1号。',
      entities: [{ id: 200, name: '关向应故居纪念馆', type: '红色场馆' }]
    }
  }
  
  // 处理上下文
  let enhancedQuestion = question
  if (context && context.lastEntity) {
    const lastEntityName = context.lastEntity.name
    if (question.includes('他') || question.includes('纪念馆')) {
      enhancedQuestion = `${lastEntityName}的${question.replace('他', '')}`
    }
  }
  
  // 简单匹配
  for (const [key, value] of Object.entries(knowledge)) {
    if (enhancedQuestion.includes(key) || question.includes(key)) {
      return {
        answer: value.answer,
        evidence_hits: [
          { id: `node_${value.entities[0].id}`, text: value.answer }
        ],
        entities: value.entities
      }
    }
  }
  
  return {
    answer: `关于“${question}”的问题，正在查询知识图谱...`,
    evidence_hits: [],
    entities: []
  }
}

// 获取实体详情
export const getEntityDetail = async (entityId) => {
  try {
    console.log('📢 获取实体详情:', entityId)
    const response = await apiClient.get(`/entity/${entityId}`)
    console.log('✅ 实体详情:', response.data)
    return response.data
  } catch (error) {
    console.error('❌ 获取实体详情失败:', error)
    
    // 返回模拟数据
    const mockEntities = {
      300: {
        id: 300,
        name: '关向应',
        labels: ['红色人物'],
        props: {
          出生时间: '1902年',
          逝世时间: '1946年',
          籍贯: '大连金州',
          入党时间: '1924年',
          逝世地点: '延安',
          职务: '红二方面军总政治委员'
        },
        relations: [
          { type: '出生时间', direction: 'outgoing', target: { name: '1902年' } },
          { type: '籍贯', direction: 'outgoing', target: { name: '金州区' } },
          { type: '相关场馆', direction: 'outgoing', target: { name: '关向应故居纪念馆' } }
        ]
      },
      200: {
        id: 200,
        name: '关向应故居纪念馆',
        labels: ['红色场馆'],
        props: {
          开放时间: '9:00-16:30（每周一闭馆）',
          联系电话: '0411-66661902',
          地址: '大连市金州区向应街道关家村1号',
          门票政策: '免费（需提前预约）',
          交通方式: '乘坐金州公交105路至向应街道站'
        },
        relations: [
          { type: '纪念人物', direction: 'outgoing', target: { name: '关向应' } }
        ]
      }
    }
    
    return mockEntities[entityId] || {
      id: entityId,
      name: `实体_${entityId}`,
      labels: ['未知'],
      props: {},
      relations: []
    }
  }
}

// 搜索实体
export const searchEntities = async (keyword) => {
  try {
    const response = await apiClient.get('/search', { params: { keyword } })
    return response.data
  } catch (error) {
    console.error('搜索实体失败:', error)
    return []
  }
}

// 获取统计信息
export const getStats = async () => {
  try {
    const response = await apiClient.get('/stats')
    return response.data
  } catch (error) {
    console.error('获取统计信息失败:', error)
    return {
      total_nodes: 0,
      total_relations: 0,
      node_types: {},
      relation_types: {}
    }
  }
}