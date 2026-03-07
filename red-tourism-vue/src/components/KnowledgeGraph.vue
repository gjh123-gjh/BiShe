<template>
  <div class="knowledge-graph">
    <!-- 图谱容器 -->
    <div ref="graphContainer" class="graph-container"></div>

    <!-- 控制面板 -->
    <div class="graph-controls" v-if="graphData.nodes && graphData.nodes.length > 0">
      <el-tooltip content="缩放重置" placement="left">
        <el-button circle size="small" @click="resetZoom">
          <el-icon><ZoomOut /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="适应屏幕" placement="left">
        <el-button circle size="small" @click="fitView">
          <el-icon><FullScreen /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="重新布局" placement="left">
        <el-button circle size="small" @click="restartSimulation">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </el-tooltip>
    </div>

    <!-- 图例 - 修复显示问题 -->
    <div class="graph-legend" v-if="graphData.nodes && graphData.nodes.length > 0">
      <div class="legend-title">图例</div>
      <div class="legend-items">
        <div v-for="item in legendItems" :key="item.type" class="legend-item">
          <div class="legend-color" :style="{ backgroundColor: item.color }"></div>
          <span class="legend-label">{{ item.label }}</span>
        </div>
      </div>
    </div>

    <!-- 调试信息 -->
    <div class="debug-info" v-if="graphData.nodes">
      <div>节点: {{ graphData.nodes.length }}</div>
      <div>关系: {{ graphData.edges.length }}</div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import * as d3 from 'd3'
import { ZoomOut, FullScreen, Refresh } from '@element-plus/icons-vue'

export default {
  name: 'KnowledgeGraph',
  props: {
    graphData: {
      type: Object,
      required: true,
      default: () => ({ nodes: [], edges: [] })
    },
    highlightedNodeIds: {
      type: Array,
      default: () => []
    }
  },
  emits: ['node-click'],
  setup(props, { emit }) {
    const graphContainer = ref(null)
    const loading = ref(false)
    
    // D3 相关变量
    let svg = null
    let simulation = null
    let zoom = null
    let width = 0
    let height = 0
    let nodeElements = null
    let linkElements = null
    let labelElements = null

    // 图例配置
    const legendItems = [
      { type: '红色场馆', color: '#ff6b6b', label: '红色场馆' },
      { type: '红色人物', color: '#4ecdc4', label: '红色人物' },
      { type: '历史事件', color: '#45b7d1', label: '历史事件' },
      { type: '红色展品', color: '#96ceb4', label: '红色展品' },
      { type: '时间', color: '#ffeaa7', label: '时间' },
      { type: '地点', color: '#dfe6e9', label: '地点' },
      { type: '旅游服务', color: '#fab1a0', label: '旅游服务' }
    ]

    // 颜色映射
    const colorMap = {
      '红色场馆': '#ff6b6b',
      '红色人物': '#4ecdc4',
      '历史事件': '#45b7d1',
      '红色展品': '#96ceb4',
      '时间': '#ffeaa7',
      '地点': '#dfe6e9',
      '旅游服务': '#fab1a0'
    }

    // 获取节点颜色
    const getNodeColor = (type) => {
      return colorMap[type] || '#95a5a6'
    }

    // 获取节点大小（根据关系数量）
    const getNodeSize = (node, allEdges) => {
      const baseSize = 15
      const relationCount = allEdges.filter(
        e => e.source.id === node.id || e.target.id === node.id
      ).length
      return baseSize + Math.min(relationCount * 2, 20)
    }

    // 高亮特定节点
    const highlightNodes = (nodeIds) => {
      if (!nodeElements) return
      
      nodeElements.attr('opacity', d => nodeIds.includes(d.id) ? 1 : 0.3)
        .attr('stroke', d => nodeIds.includes(d.id) ? '#ffd700' : '#fff')
        .attr('stroke-width', d => nodeIds.includes(d.id) ? 3 : 1.5)
      
      if (linkElements) {
        linkElements.attr('opacity', 0.2)
        linkElements.attr('stroke', '#666')
      }
      
      if (labelElements) {
        labelElements.attr('opacity', d => nodeIds.includes(d.id) ? 1 : 0.3)
          .attr('font-weight', d => nodeIds.includes(d.id) ? 'bold' : 'normal')
      }
    }

    // 拖拽函数
    const dragstarted = (event) => {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      event.subject.fx = event.subject.x
      event.subject.fy = event.subject.y
    }

    const dragged = (event) => {
      event.subject.fx = event.x
      event.subject.fy = event.y
    }

    const dragended = (event) => {
      if (!event.active) simulation.alphaTarget(0)
      event.subject.fx = null
      event.subject.fy = null
    }

    // 初始化图谱
    // 初始化图谱
    const initGraph = () => {
      if (!graphContainer.value) {
        console.error('❌ 容器不存在')
        return
      }

      if (!props.graphData.nodes || props.graphData.nodes.length === 0) {
        console.log('⚠️ 没有节点数据，跳过渲染')
        return
      }

      try {
        // 获取容器尺寸
        width = graphContainer.value.clientWidth
        height = graphContainer.value.clientHeight
        
        if (width === 0 || height === 0) {
          console.warn('⚠️ 容器尺寸为0，等待下次渲染')
          setTimeout(initGraph, 100)
          return
        }

        console.log('📏 容器尺寸:', width, 'x', height)
        console.log('📊 原始数据 - 节点数:', props.graphData.nodes.length)
        console.log('📊 原始数据 - 关系数:', props.graphData.edges.length)

        // 清除旧图
        d3.select(graphContainer.value).selectAll('*').remove()

        // 创建SVG
        svg = d3.select(graphContainer.value)
          .append('svg')
          .attr('width', width)
          .attr('height', height)
          .attr('shape-rendering', 'geometricPrecision')
          .style('background-color', '#f8f9fa')

        // 创建主容器组
        const g = svg.append('g')

        // 设置缩放
        zoom = d3.zoom()
          .scaleExtent([0.1, 4])
          .on('zoom', (event) => {
            g.attr('transform', event.transform)
          })
        svg.call(zoom)

        // 获取所有有效的节点ID
        const validNodeIds = new Set(props.graphData.nodes.map(node => node.id))
        console.log('✅ 有效节点ID:', Array.from(validNodeIds))

        // 转换节点数据
        const nodes = props.graphData.nodes.map(node => ({
          ...node,
          id: node.id,
          name: node.name || node.props?.名称 || node.props?.实体名称 || `节点_${node.id}`,
          type: node.labels?.[0] || '未知',
          props: node.props || {}
        }))

        // 过滤并转换关系数据 - 只保留源和目标都存在的边
        const edges = props.graphData.edges
          .filter(edge => {
            // 获取源和目标ID
            const sourceId = edge.source
            const targetId = edge.target
            
            // 如果 source/target 是对象，取其 id
            const sourceNodeId = typeof sourceId === 'object' ? sourceId.id : sourceId
            const targetNodeId = typeof targetId === 'object' ? targetId.id : targetId
            
            const sourceValid = validNodeIds.has(sourceNodeId)
            const targetValid = validNodeIds.has(targetNodeId)
            
            if (!sourceValid || !targetValid) {
              console.warn('⚠️ 跳过无效关系:', {
                源ID: sourceNodeId,
                目标ID: targetNodeId,
                源有效: sourceValid,
                目标有效: targetValid,
                关系类型: edge.type
              })
            }
            return sourceValid && targetValid
          })
          .map(edge => {
            const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source
            const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target
            
            return {
              source: sourceId,
              target: targetId,
              type: edge.type || '关系',
              props: edge.props || {}
            }
          })

        console.log('🔄 处理后节点数:', nodes.length)
        console.log('🔄 处理后关系数:', edges.length)
        
        if (edges.length > 0) {
          console.log('📝 关系示例:', edges[0])
        }

        // 如果没有有效的节点，返回
        if (nodes.length === 0) {
          console.error('❌ 没有有效节点')
          return
        }

        // 创建力导向图
        simulation = d3.forceSimulation(nodes)
          .force('charge', d3.forceManyBody().strength(-400))
          .force('center', d3.forceCenter(width / 2, height / 2))
          .force('collision', d3.forceCollide().radius(70))

        // 如果有关系，添加连线力
        if (edges.length > 0) {
          simulation.force('link', d3.forceLink(edges).id(d => d.id).distance(180))
          
          // 绘制连线
          linkElements = g.append('g')
            .selectAll('line')
            .data(edges)
            .enter()
            .append('line')
            .attr('stroke', '#666')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', 2)
            .attr('stroke-linecap', 'round')

          // 绘制连线标签
          const linkText = g.append('g')
            .selectAll('text')
            .data(edges)
            .enter()
            .append('text')
            .text(d => d.type)
            .attr('font-size', 10)
            .attr('fill', '#333')
            .attr('text-anchor', 'middle')
            .attr('dy', -5)
            .attr('stroke', '#fff')
            .attr('stroke-width', 0.5)
            .attr('paint-order', 'stroke')
            .style('pointer-events', 'none')
        } else {
          console.log('⚠️ 没有关系数据，只显示节点')
          linkElements = null
        }

        // 绘制节点
        nodeElements = g.append('g')
          .selectAll('circle')
          .data(nodes)
          .enter()
          .append('circle')
          .attr('r', d => {
            const size = 15 + (edges.filter(e => e.source === d.id || e.target === d.id).length * 2)
            return Math.min(size, 30)
          })
          .attr('fill', d => getNodeColor(d.type))
          .attr('stroke', '#fff')
          .attr('stroke-width', 2)
          .attr('cursor', 'pointer')
          .on('click', (event, d) => {
            event.stopPropagation()
            console.log('👆 节点点击:', d.name)
            emit('node-click', d)
          })
          .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended))

        // 绘制节点标签
        labelElements = g.append('g')
          .selectAll('text')
          .data(nodes)
          .enter()
          .append('text')
          .text(d => d.name)
          .attr('font-size', 12)
          .attr('font-weight', '500')
          .attr('fill', '#333')
          .attr('text-anchor', 'middle')
          .attr('dy', d => {
            const size = 15 + (edges.filter(e => e.source === d.id || e.target === d.id).length * 2)
            return Math.min(size, 30) + 15
          })
          .attr('stroke', '#fff')
          .attr('stroke-width', 1)
          .attr('paint-order', 'stroke')
          .style('pointer-events', 'none')
          .style('text-shadow', '1px 1px 2px rgba(255,255,255,0.8)')

        // 更新位置
        simulation.on('tick', () => {
          // 更新连线位置
          if (linkElements) {
            linkElements
              .attr('x1', d => d.source.x)
              .attr('y1', d => d.source.y)
              .attr('x2', d => d.target.x)
              .attr('y2', d => d.target.y)
          }

          // 更新连线标签位置
          if (linkElements) {
            g.selectAll('text').each(function(d) {
              if (d.source && d.target) {
                d3.select(this)
                  .attr('x', (d.source.x + d.target.x) / 2)
                  .attr('y', (d.source.y + d.target.y) / 2)
              }
            })
          }

          // 更新节点位置
          nodeElements
            .attr('cx', d => d.x)
            .attr('cy', d => d.y)

          // 更新标签位置
          labelElements
            .attr('x', d => d.x)
            .attr('y', d => d.y)
        })

        // 如果有初始高亮节点
        if (props.highlightedNodeIds && props.highlightedNodeIds.length > 0) {
          setTimeout(() => {
            highlightNodes(props.highlightedNodeIds)
          }, 500)
        }

        console.log('✅ 图谱渲染完成，节点数:', nodes.length, '关系数:', edges.length)

      } catch (error) {
        console.error('❌ 渲染图谱时出错:', error)
      }
    }

    // 重置缩放
    const resetZoom = () => {
      if (svg && zoom) {
        svg.transition()
          .duration(750)
          .call(zoom.transform, d3.zoomIdentity)
      }
    }

    // 适应屏幕
    const fitView = () => {
      if (!simulation || !svg || !zoom) return
      
      svg.transition()
        .duration(750)
        .call(zoom.transform, d3.zoomIdentity.translate(width/2, height/2).scale(0.8))
    }

    // 重新启动仿真
    const restartSimulation = () => {
      if (simulation) {
        simulation.alpha(1).restart()
      }
    }

    // 清理资源
    onBeforeUnmount(() => {
      if (simulation) {
        simulation.stop()
      }
    })

    // 监听数据变化
    watch(() => props.graphData, (newData) => {
      console.log('📊 图谱数据更新')
      nextTick(() => {
        initGraph()
      })
    }, { deep: true })

    // 监听高亮节点变化
    watch(() => props.highlightedNodeIds, (newIds) => {
      if (newIds && newIds.length > 0 && nodeElements) {
        highlightNodes(newIds)
      }
    }, { deep: true })

    // 监听窗口大小变化
    onMounted(() => {
      initGraph()
      
      window.addEventListener('resize', () => {
        if (simulation && graphContainer.value) {
          width = graphContainer.value.clientWidth
          height = graphContainer.value.clientHeight
          svg?.attr('width', width).attr('height', height)
          simulation.force('center', d3.forceCenter(width / 2, height / 2))
          simulation.alpha(0.3).restart()
        }
      })
    })

    return {
      graphContainer,
      loading,
      legendItems,
      resetZoom,
      fitView,
      restartSimulation,
      highlightNodes
    }
  }
}
</script>

<style scoped>
.knowledge-graph {
  width: 100%;
  height: 100%;
  position: relative;
  background-color: #1a1a2e;
  overflow: hidden;
}

.graph-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  padding: 20px;
}

.no-data {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1a2e;
}

.graph-controls {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  padding: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.3);
  display: flex;
  gap: 8px;
  z-index: 10;
  backdrop-filter: blur(5px);
}

/* 修复图例样式 */
.graph-legend {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.3);
  z-index: 10;
  backdrop-filter: blur(5px);
  min-width: 150px;
  border: 1px solid rgba(255,255,255,0.1);
}

.legend-title {
  font-weight: bold;
  margin-bottom: 8px;
  color: #333;
  font-size: 14px;
  padding-bottom: 4px;
  border-bottom: 1px solid #eee;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.legend-label {
  color: #333;
  font-weight: 500;
}

.debug-info {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(0,0,0,0.7);
  color: #fff;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 10;
  font-family: monospace;
  line-height: 1.5;
  border: 1px solid rgba(255,255,255,0.1);
}

.debug-info div {
  margin: 2px 0;
}

/* 按钮样式 */
:deep(.el-button) {
  padding: 8px;
}
</style>