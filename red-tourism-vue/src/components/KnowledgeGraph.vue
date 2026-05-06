<template>
  <div class="knowledge-graph">
    <div ref="graphContainer" class="graph-container"></div>

    <div class="graph-controls" v-if="graphData.nodes && graphData.nodes.length > 0">
      <el-tooltip v-if="subgraphActive" content="恢复显示完整知识图谱" placement="left">
        <el-button type="warning" size="small" round @click="onRestoreFullGraph">
          显示完整图谱
        </el-button>
      </el-tooltip>
      <div v-if="subgraphActive" class="one-hop-switch">
        <el-switch
          :model-value="includeOneHopNeighbors"
          inline-prompt
          size="small"
          active-text="含一跳邻居"
          inactive-text="仅命中节点"
          @update:model-value="$emit('update:includeOneHopNeighbors', $event)"
        />
      </div>
      <el-dropdown trigger="click" @command="onExportCommand">
        <el-button circle size="small" title="导出当前视图">
          <el-icon><Download /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="svg">导出 SVG（矢量）</el-dropdown-item>
            <el-dropdown-item command="png">导出 PNG（2× 分辨率）</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
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

    <div class="graph-legend" v-if="graphData.nodes && graphData.nodes.length > 0">
      <div class="legend-title">节点类型</div>
      <div class="legend-items">
        <div v-for="item in legendItems" :key="item.type" class="legend-item">
          <span class="legend-shape" :class="'shape-' + item.shapeKey" :style="{ borderColor: item.color, background: item.color }" />
          <span class="legend-label">{{ item.label }}</span>
        </div>
      </div>
    </div>

    <div v-if="subgraphActive || (evidenceFocusNodeIds && evidenceFocusNodeIds.length)" class="subgraph-hint">
      <span v-if="subgraphActive" class="hint-text">当前为「问答相关子图」</span>
      <el-button
        v-if="evidenceFocusNodeIds && evidenceFocusNodeIds.length"
        link
        type="warning"
        size="small"
        class="hint-clear"
        @click="$emit('clear-evidence-focus')"
      >
        清除证据高亮
      </el-button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import * as d3 from 'd3'
import { ZoomOut, FullScreen, Refresh, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'KnowledgeGraph',
  components: { ZoomOut, FullScreen, Refresh, Download },
  props: {
    graphData: {
      type: Object,
      required: true,
      default: () => ({ nodes: [], edges: [] })
    },
    /** 问答命中实体，用于加粗高亮描边 */
    primaryNodeIds: {
      type: Array,
      default: () => []
    },
    subgraphActive: {
      type: Boolean,
      default: false
    },
    includeOneHopNeighbors: {
      type: Boolean,
      default: false
    },
    /** 点击证据后仅强调的节点（其余变淡） */
    evidenceFocusNodeIds: {
      type: Array,
      default: () => []
    }
  },
  emits: ['node-click', 'restore-full-graph', 'update:includeOneHopNeighbors', 'clear-evidence-focus'],
  setup(props, { emit }) {
    const graphContainer = ref(null)
    const loading = ref(false)

    let svg = null
    let gRoot = null
    let simulation = null
    let zoom = null
    let width = 0
    let height = 0
    let nodeJoin = null
    let linkJoin = null
    let linkLabelJoin = null
    let labelJoin = null
    let lastNodes = []

    const colorMap = {
      红色场馆: '#e74c3c',
      红色人物: '#1abc9c',
      历史事件: '#3498db',
      红色展品: '#27ae60',
      时间: '#f39c12',
      地点: '#9b59b6',
      旅游服务: '#e67e22',
      未知: '#95a5a6'
    }

    const shapeTypeMap = {
      红色人物: d3.symbolCircle,
      红色场馆: d3.symbolSquare,
      历史事件: d3.symbolDiamond,
      红色展品: d3.symbolTriangle,
      时间: d3.symbolWye,
      地点: d3.symbolCross,
      旅游服务: d3.symbolStar,
      未知: d3.symbolCircle
    }

    const legendItems = [
      { type: '红色场馆', label: '红色场馆', color: colorMap['红色场馆'], shapeKey: 'square' },
      { type: '红色人物', label: '红色人物', color: colorMap['红色人物'], shapeKey: 'circle' },
      { type: '历史事件', label: '历史事件', color: colorMap['历史事件'], shapeKey: 'diamond' },
      { type: '红色展品', label: '红色展品', color: colorMap['红色展品'], shapeKey: 'triangle' },
      { type: '时间', label: '时间', color: colorMap['时间'], shapeKey: 'wye' },
      { type: '地点', label: '地点', color: colorMap['地点'], shapeKey: 'cross' },
      { type: '旅游服务', label: '旅游服务', color: colorMap['旅游服务'], shapeKey: 'star' }
    ]

    const linkColorMap = {
      出生于: '#1abc9c',
      逝世于: '#7f8c8d',
      位于: '#9b59b6',
      发生于: '#3498db',
      属于: '#e67e22',
      相关: '#34495e',
      相关人物: '#16a085',
      相关场馆: '#c0392b',
      相关事件: '#2980b9',
      展出: '#27ae60',
      时间: '#f39c12',
      籍贯: '#8e44ad',
      出生时间: '#1abc9c',
      逝世时间: '#95a5a6',
      地址: '#9b59b6',
      陈列于: '#8e44ad',
      收藏品: '#16a085'
    }

    const idKey = (id) => (id === undefined || id === null ? '' : String(id))

    const hashStr = (s) => {
      let h = 0
      const str = String(s || '')
      for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0
      return Math.abs(h)
    }

    const computeLinkGeom = (d) => {
      const x1 = d.source.x
      const y1 = d.source.y
      const x2 = d.target.x
      const y2 = d.target.y
      const dx = x2 - x1
      const dy = y2 - y1
      const len = Math.sqrt(dx * dx + dy * dy) || 1
      const nx = -dy / len
      const ny = dx / len
      const midx = (x1 + x2) / 2
      const midy = (y1 + y2) / 2
      const pairIdx = d._samePairIndex || 0
      const arcBase = 36 + pairIdx * 16
      const bias = (d._arcSign || 1) * arcBase
      const cx = midx + nx * bias
      const cy = midy + ny * bias
      const lx = 0.25 * x1 + 0.5 * cx + 0.25 * x2
      const ly = 0.25 * y1 + 0.5 * cy + 0.25 * y2
      const labelOff = 12 + ((d._linkIdx || 0) % 7) * 7
      return {
        path: `M${x1},${y1} Q${cx},${cy} ${x2},${y2}`,
        labelX: lx + nx * labelOff,
        labelY: ly + ny * labelOff
      }
    }

    const edgeEndpointId = (end) => {
      if (end == null) return ''
      if (typeof end === 'object' && end.id != null) return idKey(end.id)
      return idKey(end)
    }

    const primarySet = () => new Set((props.primaryNodeIds || []).map(idKey))

    const evidenceSet = () => new Set((props.evidenceFocusNodeIds || []).map(idKey))

    const getNodeType = (node) => node.labels?.[0] || '未知'

    const getNodeColor = (type) => colorMap[type] || colorMap['未知']

    const getSymbolType = (type) => shapeTypeMap[type] || shapeTypeMap['未知']

    const getLinkColor = (relType) => {
      const t = (relType || '关系').trim()
      return linkColorMap[t] || '#7f8c8d'
    }

    const nodeSymbolSize = (d, edges) => {
      const deg = edges.filter(
        (e) => edgeEndpointId(e.source) === idKey(d.id) || edgeEndpointId(e.target) === idKey(d.id)
      ).length
      const base = props.subgraphActive ? 320 : 260
      return Math.min(base + deg * 42, 720)
    }

    const applyNodeLinkStyles = () => {
      const es = evidenceSet()
      const ps = primarySet()
      if (!nodeJoin) return

      if (es.size > 0) {
        nodeJoin.select('path').each(function (d) {
          const inE = es.has(idKey(d.id))
          d3.select(this)
            .attr('stroke', inE ? '#0891b2' : '#cbd5e1')
            .attr('stroke-width', inE ? 4 : 1)
            .attr('fill-opacity', inE ? 0.95 : 0.28)
        })
        labelJoin?.attr('opacity', (d) => (es.has(idKey(d.id)) ? 1 : 0.32))
        linkJoin?.attr('stroke-opacity', (d) => {
          const a = edgeEndpointId(d.source)
          const b = edgeEndpointId(d.target)
          return es.has(a) || es.has(b) ? 0.88 : 0.06
        })
        linkLabelJoin?.attr('opacity', (d) => {
          const a = edgeEndpointId(d.source)
          const b = edgeEndpointId(d.target)
          return es.has(a) || es.has(b) ? 1 : 0.15
        })
        return
      }

      labelJoin?.attr('opacity', 1)
      linkJoin?.attr('stroke-opacity', 0.75)
      linkLabelJoin?.attr('opacity', 1)

      if (!ps.size) {
        nodeJoin.select('path')
          .attr('stroke-width', 2)
          .attr('stroke', '#64748b')
          .attr('fill-opacity', 0.92)
        return
      }
      nodeJoin.select('path').each(function (d) {
        const isP = ps.has(idKey(d.id))
        d3.select(this)
          .attr('stroke', isP ? '#d97706' : '#94a3b8')
          .attr('stroke-width', isP ? 3.2 : 1.8)
          .attr('fill-opacity', 0.92)
      })
    }

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

    const initGraph = () => {
      if (!graphContainer.value) return

      if (!props.graphData.nodes || props.graphData.nodes.length === 0) {
        d3.select(graphContainer.value).selectAll('*').remove()
        return
      }

      width = graphContainer.value.clientWidth
      height = graphContainer.value.clientHeight

      if (width === 0 || height === 0) {
        setTimeout(initGraph, 100)
        return
      }

      d3.select(graphContainer.value).selectAll('*').remove()

      svg = d3
        .select(graphContainer.value)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('shape-rendering', 'geometricPrecision')
        .style('background-color', '#ffffff')

      gRoot = svg.append('g').attr('class', 'kg-zoom-layer')

      zoom = d3
        .zoom()
        .scaleExtent([0.12, 5])
        .on('zoom', (event) => {
          gRoot.attr('transform', event.transform)
        })
      svg.call(zoom)

      const validNodeIds = new Set(props.graphData.nodes.map((n) => idKey(n.id)))

      const nodes = props.graphData.nodes.map((node) => ({
        ...node,
        id: node.id,
        name: node.name || node.props?.名称 || node.props?.实体名称 || `节点_${node.id}`,
        type: getNodeType(node),
        props: node.props || {}
      }))

      const edges = props.graphData.edges
        .filter((edge) => {
          const sourceNodeId = typeof edge.source === 'object' ? edge.source.id : edge.source
          const targetNodeId = typeof edge.target === 'object' ? edge.target.id : edge.target
          return validNodeIds.has(idKey(sourceNodeId)) && validNodeIds.has(idKey(targetNodeId))
        })
        .map((edge) => {
          const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source
          const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target
          return {
            source: sourceId,
            target: targetId,
            type: edge.type || '关系',
            props: edge.props || {}
          }
        })

      const nodeById = new Map(nodes.map((n) => [idKey(n.id), n]))
      edges.forEach((e, i) => {
        e._linkIdx = i
        const a = idKey(e.source)
        const b = idKey(e.target)
        e._pairKey = a < b ? `${a}|${b}` : `${b}|${a}`
      })
      const pairCnt = {}
      edges.forEach((e) => {
        const n = pairCnt[e._pairKey] || 0
        e._samePairIndex = n
        pairCnt[e._pairKey] = n + 1
        e._arcSign = n % 2 === 0 ? 1 : -1
      })

      lastNodes = nodes

      const linkForce = d3
        .forceLink(edges)
        .id((d) => d.id)
        .distance((d) => {
          const s = typeof d.source === 'object' ? d.source : nodeById.get(idKey(d.source))
          const t = typeof d.target === 'object' ? d.target : nodeById.get(idKey(d.target))
          const lens = ((s && s.name) || '').length + ((t && t.name) || '').length
          const base = props.subgraphActive ? 160 : 220
          return Math.min(base + lens * 5, 480)
        })
        .strength(0.55)

      simulation = d3
        .forceSimulation(nodes)
        .force('charge', d3.forceManyBody().strength(props.subgraphActive ? -520 : -820))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force(
          'collision',
          d3.forceCollide().radius((d) => Math.sqrt(nodeSymbolSize(d, edges) / Math.PI) + 28)
        )
        .force('link', linkForce)

      const glinks = gRoot.append('g').attr('class', 'kg-links')

      linkJoin = glinks
        .selectAll('path.kg-link')
        .data(edges)
        .enter()
        .append('path')
        .attr('class', 'kg-link')
        .attr('fill', 'none')
        .attr('stroke', (d) => getLinkColor(d.type))
        .attr('stroke-opacity', 0.78)
        .attr('stroke-width', 2)
        .attr('stroke-linecap', 'round')

      const glinkLabels = gRoot.append('g').attr('class', 'kg-link-labels')

      linkLabelJoin = glinkLabels
        .selectAll('text.kg-link-label')
        .data(edges)
        .enter()
        .append('text')
        .attr('class', 'kg-link-label')
        .text((d) => d.type)
        .attr('font-size', 10)
        .attr('font-weight', '600')
        .attr('fill', '#334155')
        .attr('text-anchor', 'middle')
        .attr('dy', 3)
        .attr('stroke', '#ffffff')
        .attr('stroke-width', 4)
        .attr('paint-order', 'stroke')
        .style('pointer-events', 'none')

      const gnodes = gRoot.append('g').attr('class', 'kg-nodes')

      const sym = d3.symbol()

      nodeJoin = gnodes
        .selectAll('g.kg-node')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', 'kg-node')
        .attr('cursor', 'pointer')
        .on('click', (event, d) => {
          event.stopPropagation()
          emit('node-click', d)
        })
        .call(d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended))

      nodeJoin
        .append('path')
        .attr('d', (d) => {
          const t = getSymbolType(d.type)
          const sz = nodeSymbolSize(d, edges)
          return sym.type(t).size(sz)()
        })
        .attr('fill', (d) => getNodeColor(d.type))
        .attr('fill-opacity', 0.92)
        .attr('stroke', '#64748b')
        .attr('stroke-width', 2)

      const glabels = gRoot.append('g').attr('class', 'kg-node-labels')

      const labelEnter = glabels
        .selectAll('text.kg-node-label')
        .data(nodes)
        .enter()
        .append('text')
        .attr('class', 'kg-node-label')

      labelEnter.text((d) => {
        const n = d.name || ''
        return n.length > 14 ? `${n.slice(0, 13)}…` : n
      })
      labelEnter.each(function (d) {
        d3.select(this).append('title').text(d.name || '')
      })
      labelJoin = glabels
        .selectAll('text.kg-node-label')
        .attr('font-size', 11)
        .attr('font-weight', '600')
        .attr('fill', '#0f172a')
        .attr('text-anchor', 'middle')
        .attr('stroke', '#ffffff')
        .attr('stroke-width', 3)
        .attr('paint-order', 'stroke')
        .style('pointer-events', 'none')

      simulation.on('tick', () => {
        linkJoin.attr('d', (d) => computeLinkGeom(d).path)

        linkLabelJoin
          .attr('x', (d) => computeLinkGeom(d).labelX)
          .attr('y', (d) => computeLinkGeom(d).labelY)

        nodeJoin.attr('transform', (d) => `translate(${d.x},${d.y})`)

        labelJoin.attr('x', (d) => d.x).attr('y', (d) => {
          const r = Math.sqrt(nodeSymbolSize(d, edges) / Math.PI)
          const base = d.y + r + 12
          return base + (hashStr(d.id) % 7) * 5
        })
      })

      applyNodeLinkStyles()

      nextTick(() => {
        fitView()
        setTimeout(fitView, 450)
      })
    }

    const resetZoom = () => {
      if (svg && zoom) {
        svg.transition().duration(450).call(zoom.transform, d3.zoomIdentity)
      }
    }

    const fitView = () => {
      if (!svg || !zoom || !gRoot || !lastNodes.length) return

      const pad = 48
      let minX = Infinity
      let minY = Infinity
      let maxX = -Infinity
      let maxY = -Infinity

      lastNodes.forEach((d) => {
        if (d.x == null || d.y == null) return
        const r = 28
        minX = Math.min(minX, d.x - r)
        minY = Math.min(minY, d.y - r)
        maxX = Math.max(maxX, d.x + r)
        maxY = Math.max(maxY, d.y + r)
      })

      if (!Number.isFinite(minX)) {
        svg.transition().duration(450).call(zoom.transform, d3.zoomIdentity.translate(width / 2, height / 2).scale(0.9))
        return
      }

      const w = maxX - minX + pad * 2
      const h = maxY - minY + pad * 2
      const midX = (minX + maxX) / 2
      const midY = (minY + maxY) / 2
      const scale = Math.min(width / w, height / h, 1.8) * 0.92
      const tx = width / 2 - scale * midX
      const ty = height / 2 - scale * midY

      svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale))
    }

    const restartSimulation = () => {
      if (simulation) simulation.alpha(1).restart()
    }

    const onRestoreFullGraph = () => {
      emit('restore-full-graph')
    }

    const fitViewToNodeIds = (ids) => {
      if (!svg || !zoom || !lastNodes.length) return
      const set = new Set((ids || []).map(idKey))
      const subset = lastNodes.filter((d) => set.has(idKey(d.id)))
      if (!subset.length) return

      const pad = 56
      let minX = Infinity
      let minY = Infinity
      let maxX = -Infinity
      let maxY = -Infinity
      subset.forEach((d) => {
        if (d.x == null || d.y == null) return
        const r = 36
        minX = Math.min(minX, d.x - r)
        minY = Math.min(minY, d.y - r)
        maxX = Math.max(maxX, d.x + r)
        maxY = Math.max(maxY, d.y + r)
      })
      if (!Number.isFinite(minX)) return

      const w = maxX - minX + pad * 2
      const h = maxY - minY + pad * 2
      const midX = (minX + maxX) / 2
      const midY = (minY + maxY) / 2
      const scale = Math.min(width / w, height / h, 2.2) * 0.88
      const tx = width / 2 - scale * midX
      const ty = height / 2 - scale * midY
      svg.transition().duration(480).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale))
    }

    const exportSvg = () => {
      const svgEl = graphContainer.value?.querySelector('svg')
      if (!svgEl) {
        ElMessage.warning('暂无可导出的图谱')
        return
      }
      const clone = svgEl.cloneNode(true)
      const serializer = new XMLSerializer()
      let out = serializer.serializeToString(clone)
      if (!out.includes('xmlns="http://www.w3.org/2000/svg"')) {
        out = out.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
      }
      const blob = new Blob([out], { type: 'image/svg+xml;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `知识图谱_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.svg`
      a.click()
      URL.revokeObjectURL(url)
      ElMessage.success('已下载 SVG')
    }

    const exportPng = () => {
      const svgEl = graphContainer.value?.querySelector('svg')
      if (!svgEl) {
        ElMessage.warning('暂无可导出的图谱')
        return
      }
      const rect = svgEl.getBoundingClientRect()
      const clone = svgEl.cloneNode(true)
      const serializer = new XMLSerializer()
      let source = serializer.serializeToString(clone)
      if (!source.includes('xmlns="http://www.w3.org/2000/svg"')) {
        source = source.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
      }
      const svgBlob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' })
      const url = URL.createObjectURL(svgBlob)
      const img = new Image()
      img.onload = () => {
        const scale = 2
        const canvas = document.createElement('canvas')
        canvas.width = Math.max(1, Math.floor(rect.width * scale))
        canvas.height = Math.max(1, Math.floor(rect.height * scale))
        const ctx = canvas.getContext('2d')
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
        URL.revokeObjectURL(url)
        canvas.toBlob((blob) => {
          if (!blob) {
            ElMessage.error('PNG 导出失败')
            return
          }
          const a = document.createElement('a')
          a.href = URL.createObjectURL(blob)
          a.download = `知识图谱_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.png`
          a.click()
          URL.revokeObjectURL(a.href)
          ElMessage.success('已下载 PNG')
        }, 'image/png')
      }
      img.onerror = () => {
        URL.revokeObjectURL(url)
        ElMessage.error('PNG 渲染失败，可尝试导出 SVG')
      }
      img.src = url
    }

    const onExportCommand = (cmd) => {
      if (cmd === 'svg') exportSvg()
      else if (cmd === 'png') exportPng()
    }

    onBeforeUnmount(() => {
      if (simulation) simulation.stop()
    })

    watch(
      () => props.graphData,
      () => {
        nextTick(() => initGraph())
      },
      { deep: true }
    )

    watch(
      () => [...(props.primaryNodeIds || [])],
      () => {
        applyNodeLinkStyles()
      },
      { deep: true }
    )

    watch(
      () => [...(props.evidenceFocusNodeIds || [])],
      (ids) => {
        applyNodeLinkStyles()
        if (ids.length) {
          nextTick(() => {
            setTimeout(() => fitViewToNodeIds(ids), 80)
          })
        }
      },
      { deep: true }
    )

    onMounted(() => {
      initGraph()
      window.addEventListener('resize', () => {
        if (!graphContainer.value || !simulation) return
        width = graphContainer.value.clientWidth
        height = graphContainer.value.clientHeight
        svg?.attr('width', width).attr('height', height)
        simulation.force('center', d3.forceCenter(width / 2, height / 2))
        simulation.alpha(0.35).restart()
      })
    })

    return {
      graphContainer,
      loading,
      legendItems,
      resetZoom,
      fitView,
      fitViewToNodeIds,
      restartSimulation,
      onRestoreFullGraph,
      onExportCommand,
      exportSvg,
      exportPng,
      applyEvidenceStyles: applyNodeLinkStyles
    }
  }
}
</script>

<style scoped>
.knowledge-graph {
  width: 100%;
  height: 100%;
  position: relative;
  background-color: #ffffff;
  overflow: hidden;
}

.graph-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.graph-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  padding: 8px 10px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.12);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  z-index: 10;
  border: 1px solid #e2e8f0;
  max-width: min(360px, 92vw);
}

.graph-legend {
  position: absolute;
  bottom: 16px;
  left: 16px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  padding: 12px 14px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.12);
  z-index: 10;
  border: 1px solid #e2e8f0;
  min-width: 140px;
}

.legend-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #0f172a;
  font-size: 13px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e2e8f0;
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
  font-size: 11px;
}

.legend-shape {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  box-sizing: border-box;
  opacity: 0.95;
}

.legend-shape.shape-circle {
  border-radius: 50%;
  border: 2px solid;
  background: transparent !important;
}

.legend-shape.shape-square {
  border-radius: 2px;
  border: 2px solid;
  background: transparent !important;
}

.legend-shape.shape-diamond {
  transform: rotate(45deg);
  border-radius: 1px;
  border: 2px solid;
  background: transparent !important;
}

.legend-shape.shape-triangle {
  width: 0;
  height: 0;
  border-left: 7px solid transparent;
  border-right: 7px solid transparent;
  border-bottom: 12px solid;
  background: transparent !important;
  border-top: none;
}

.legend-shape.shape-wye,
.legend-shape.shape-cross,
.legend-shape.shape-star {
  border-radius: 2px;
  border: 2px solid;
  background: transparent !important;
}

.legend-label {
  color: #334155;
  font-weight: 500;
}

.subgraph-hint {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #b45309;
  background: rgba(254, 243, 199, 0.95);
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid #fcd34d;
  pointer-events: auto;
}

.subgraph-hint .hint-text {
  pointer-events: none;
}

.subgraph-hint .hint-clear {
  pointer-events: auto;
}

.one-hop-switch {
  display: flex;
  align-items: center;
  padding: 0 4px;
}

.one-hop-switch :deep(.el-switch) {
  --el-switch-on-color: #409eff;
}

:deep(.el-button) {
  padding: 8px;
}

:deep(.el-button--small.is-round) {
  padding: 6px 12px;
}
</style>
