<template>
  <div class="dashboard">
    <el-header class="header">
      <h1>大连红色旅游知识图谱系统</h1>
    </el-header>

    <el-container class="main-container">
      <el-aside width="30%" class="qa-section">
        <QAChat 
          @select-entity="handleSelectEntity"
        />
      </el-aside>

      <el-main class="graph-section">
        <KnowledgeGraph
          ref="knowledgeGraph"
          :graph-data="graphData"
          @node-click="handleNodeClick"
        />
      </el-main>

      <el-aside width="20%" class="detail-section">
        <EntityDetail :entity="selectedEntity" />
      </el-aside>
    </el-container>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import QAChat from '@/components/QAChat.vue'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import EntityDetail from '@/components/EntityDetail.vue'
import { fetchGraphData, getEntityDetail } from '@/services/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'DashboardView',
  components: {
    QAChat,
    KnowledgeGraph,
    EntityDetail
  },
  setup() {
    const graphData = ref({ nodes: [], edges: [] })
    const selectedEntity = ref(null)
    const knowledgeGraph = ref(null)

    // 加载图谱数据
    const loadGraphData = async () => {
      console.log('%c📢 开始加载图谱数据...', 'color: blue; font-size: 14px')
      console.log('时间:', new Date().toLocaleTimeString())
      
      try {
        const data = await fetchGraphData()
        
        console.log('%c📦 获取到的原始数据:', 'color: purple; font-size: 12px', data)
        console.log('节点数据:', data.nodes)
        console.log('关系数据:', data.edges)
        
        // 确保数据格式正确
        const formattedData = {
          nodes: data.nodes || [],
          edges: data.edges || []
        }
        
        console.log('%c✅ 格式化后的数据:', 'color: green; font-size: 12px', formattedData)
        console.log('节点数量:', formattedData.nodes.length)
        console.log('关系数量:', formattedData.edges.length)
        
        // 打印第一个节点示例（如果有）
        if (formattedData.nodes.length > 0) {
          console.log('%c🔍 第一个节点示例:', 'color: orange; font-size: 12px', formattedData.nodes[0])
          
          // 检查节点数据格式
          const firstNode = formattedData.nodes[0]
          console.log('节点ID:', firstNode.id)
          console.log('节点名称:', firstNode.name || firstNode.props?.名称 || firstNode.props?.实体名称)
          console.log('节点标签:', firstNode.labels)
          console.log('节点属性:', firstNode.props)
        }
        
        // 打印第一个关系示例（如果有）
        if (formattedData.edges.length > 0) {
          console.log('%c🔗 第一个关系示例:', 'color: orange; font-size: 12px', formattedData.edges[0])
        }
        
        graphData.value = formattedData
        
        if (formattedData.nodes.length > 0) {
          ElMessage.success(`加载成功：${formattedData.nodes.length}个节点，${formattedData.edges.length}条关系`)
          console.log('%c🎉 数据加载成功，准备渲染图谱', 'color: green; font-size: 16px; font-weight: bold')
        } else {
          ElMessage.warning('图谱数据为空')
          console.warn('%c⚠️ 图谱数据为空', 'color: orange; font-size: 14px')
        }
      } catch (error) {
        console.error('%c❌ 加载图谱数据失败:', 'color: red; font-size: 14px', error)
        console.error('错误详情:', error.message)
        console.error('错误堆栈:', error.stack)
        ElMessage.error('加载图谱数据失败')
        
        // 使用模拟数据作为后备
        console.log('%c🔄 使用模拟数据作为后备', 'color: blue; font-size: 12px')
        graphData.value = {
          nodes: [
            { id: 1, name: '关向应', labels: ['红色人物'], props: { 出生时间: '1902年', 逝世时间: '1946年' } },
            { id: 2, name: '关向应故居纪念馆', labels: ['红色场馆'], props: { 地址: '金州区向应街道' } },
            { id: 3, name: '1902年', labels: ['时间'], props: {} },
            { id: 4, name: '金州区', labels: ['地点'], props: {} }
          ],
          edges: [
            { source: 1, target: 3, type: '出生时间' },
            { source: 1, target: 4, type: '籍贯' },
            { source: 1, target: 2, type: '相关场馆' }
          ]
        }
        ElMessage.info('使用模拟数据展示')
      }
    }

    // 处理节点点击
    const handleNodeClick = async (node) => {
      console.log('%c👆 节点点击事件:', 'color: blue; font-size: 14px', node)
      console.log('节点ID:', node.id)
      console.log('节点名称:', node.name || node.props?.名称 || node.props?.实体名称)
      console.log('节点类型:', node.labels)
      
      try {
        ElMessage.info(`正在加载 ${node.name || node.props?.名称 || '节点'} 的详细信息...`)
        
        // 尝试从API获取详情
        const detail = await getEntityDetail(node.id)
        
        if (detail) {
          console.log('%c📋 获取到的实体详情:', 'color: purple; font-size: 12px', detail)
          selectedEntity.value = detail
          ElMessage.success('加载完成')
        } else {
          // 如果没有详情，至少显示节点基本信息
          console.log('使用节点基本信息作为详情')
          selectedEntity.value = {
            id: node.id,
            name: node.name || node.props?.名称 || node.props?.实体名称 || `节点_${node.id}`,
            type: node.labels?.[0] || '未知',
            props: node.props || {}
          }
          ElMessage.warning('获取详细信息失败，显示基本信息')
        }
      } catch (error) {
        console.error('❌ 获取实体详情失败:', error)
        
        // 出错时也显示基本信息
        selectedEntity.value = {
          id: node.id,
          name: node.name || node.props?.名称 || node.props?.实体名称 || `节点_${node.id}`,
          type: node.labels?.[0] || '未知',
          props: node.props || {}
        }
        ElMessage.warning('获取详细信息失败，显示基本信息')
      }
    }

    // 处理实体选择（来自问答）
    // 处理实体选择（来自问答）
    const handleSelectEntity = (entity, nodeIds) => {
      console.log('🎯 实体选择事件:', entity, '节点IDs:', nodeIds)
      
      if (entity) {
        handleNodeClick(entity)
      }
      
      // 如果有图谱实例，高亮节点
      if (knowledgeGraph.value && knowledgeGraph.value.highlightNodes) {
        if (nodeIds && nodeIds.length > 0) {
          console.log('高亮多个节点:', nodeIds)
          knowledgeGraph.value.highlightNodes(nodeIds)
        } else if (entity) {
          console.log('高亮单个节点:', entity.id)
          knowledgeGraph.value.highlightNodes([entity.id])
        }
      }
    }

    // 组件挂载时加载数据
    onMounted(() => {
      console.log('%c🟢 Dashboard 组件已挂载', 'color: green; font-size: 16px; font-weight: bold')
      loadGraphData()
    })

    return {
      graphData,
      selectedEntity,
      knowledgeGraph,
      handleNodeClick,
      handleSelectEntity
    }
  }
}
</script>

<style scoped>
.dashboard {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  z-index: 10;
}

.header h1 {
  font-size: 20px;
  margin: 0;
  font-weight: 500;
}

.main-container {
  flex: 1;
  overflow: hidden;
  height: calc(100vh - 60px);
}

.qa-section {
  background-color: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
  height: 100%;
}

.graph-section {
  background-color: #1a1a2e;
  padding: 0;
  overflow: hidden;
  height: 100%;
  position: relative;
}

.detail-section {
  background-color: #f5f7fa;
  border-left: 1px solid #e4e7ed;
  overflow-y: auto;
  height: 100%;
}

/* 自定义滚动条 */
.qa-section::-webkit-scrollbar,
.detail-section::-webkit-scrollbar {
  width: 6px;
}

.qa-section::-webkit-scrollbar-thumb,
.detail-section::-webkit-scrollbar-thumb {
  background-color: #ddd;
  border-radius: 3px;
}

.qa-section::-webkit-scrollbar-track,
.detail-section::-webkit-scrollbar-track {
  background-color: #f5f7fa;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .qa-section {
    width: 35% !important;
  }
  .detail-section {
    width: 25% !important;
  }
}

@media (max-width: 768px) {
  .qa-section {
    width: 40% !important;
  }
  .detail-section {
    width: 30% !important;
  }
}
</style>