<template>
  <div class="qa-chat">
    <!-- 对话历史 -->
    <div class="chat-history" ref="historyRef">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.type]"
      >
        <div class="message-avatar">
          <el-avatar :size="32" :src="message.type === 'user' ? userAvatar : botAvatar" />
        </div>
        <div class="message-content">
          <div class="message-bubble">{{ message.content }}</div>
          <!-- 显示证据 -->
          <div v-if="message.evidence && message.evidence.length > 0" class="message-evidence">
            <el-divider>
              <el-tag size="small" type="info">证据来源</el-tag>
            </el-divider>
            <div class="evidence-list">
              <div
                v-for="(ev, idx) in message.evidence"
                :key="idx"
                class="evidence-item evidence-item--clickable"
                role="button"
                tabindex="0"
                :title="'点击在图谱中高亮该证据对应节点'"
                @click="onEvidenceClick(ev)"
                @keyup.enter="onEvidenceClick(ev)"
              >
                {{ ev.text }}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 打字指示器 -->
      <div v-if="isLoading" class="message assistant">
        <div class="message-avatar">
          <el-avatar :size="32" :src="botAvatar" />
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="2"
        placeholder="输入您的问题..."
        @keyup.enter.prevent="sendMessage"
        :disabled="isLoading"
      />
      <div class="input-actions">
        <el-button type="primary" @click="sendMessage" :loading="isLoading">发送</el-button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { askQuestion } from '@/services/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'QAChat',
  emits: ['select-entity', 'update-context', 'focus-evidence'],
  setup(props, { emit }) {
    const messages = ref([
      {
        type: 'assistant',
        content: '您好！我是大连红色旅游知识图谱助手，请问有什么可以帮您？',
        evidence: []
      }
    ])
    const inputText = ref('')
    const isLoading = ref(false)
    
    // 添加对话上下文
    const conversationContext = ref({
      lastEntity: null,        // 上一个提到的实体
      mentionedEntities: [],    // 所有提到的实体
      topics: []               // 对话主题
    })

    const userAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'
    const botAvatar = 'https://cube.elemecdn.com/9/c2/f0ee8a3c7c9638a54940382568c9dpng.png'

    const extractNodeIdsFromEvidenceHit = (hit) => {
      if (!hit || typeof hit !== 'object') return []
      const od = hit.original_data
      const src = hit.source
      if (od && src === 'knowledge_graph_relation') {
        const a = od.source ?? od.source_id
        const b = od.target ?? od.target_id
        return [a, b].filter((x) => x !== undefined && x !== null)
      }
      if (od && od.id != null) {
        return [od.id]
      }
      const hid = String(hit.id || '')
      const m = hid.match(/node_(\d+)/i)
      if (m) return [Number(m[1])]
      return []
    }

    const collectAllEvidenceNodeIds = (hits) => {
      const s = new Set()
      for (const h of hits || []) {
        extractNodeIdsFromEvidenceHit(h).forEach((id) => s.add(id))
      }
      return [...s]
    }

    const guessNameForNode = (hits, nodeId) => {
      const key = String(nodeId)
      for (const h of hits || []) {
        const ids = extractNodeIdsFromEvidenceHit(h).map(String)
        if (!ids.includes(key)) continue
        const t = h.text || ''
        let m = t.match(/实体[：:]\s*([^\s\n,，|]+)/)
        if (m) return m[1]
        m = t.match(/关系:\s*([^\s\-—]+)\s*[-—]/)
        if (m) return m[1]
      }
      return `节点_${nodeId}`
    }

    const mergeEntitiesById = (existing, additions) => {
      const m = new Map()
      ;[...(existing || []), ...(additions || [])].forEach((e) => {
        if (e && e.id != null) m.set(e.id, e)
      })
      return Array.from(m.values())
    }

    const isArtifactLikeName = (name) =>
      /钢笔|展品|文物|纪念章|收藏品|印章|书信|手稿/.test(name || '')

    const pickFocusEntityForTurn = (merged, userQuestion, previousLast) => {
      const q = (userQuestion || '').trim()
      if (!merged.length) return null

      const bioMarkers =
        /生平|逝世|去世|事迹|干过|做过|出生|哪年|什么时候|哪天|哪些事情/.test(q)
      const people = merged.filter(
        (e) =>
          (e.type === '红色人物' || String(e.type || '').endsWith('人物')) &&
          !isArtifactLikeName(e.name)
      )
      if (bioMarkers && people.length) {
        const inQ = people.filter((e) => q.includes(e.name || ''))
        if (inQ.length) {
          return [...inQ].sort(
            (a, b) => (a.name || '').length - (b.name || '').length
          )[0]
        }
        if (previousLast && people.some((e) => e.id === previousLast.id)) {
          return merged.find((e) => e.id === previousLast.id) || previousLast
        }
        return people[0]
      }

      const candidates = merged.filter((e) => {
        const n = e.name || ''
        return n && q.includes(n)
      })
      if (candidates.length) {
        return [...candidates].sort(
          (a, b) => (a.name || '').length - (b.name || '').length
        )[0]
      }

      if (previousLast && merged.some((e) => e.id === previousLast.id)) {
        return merged.find((e) => e.id === previousLast.id)
      }

      return merged[0]
    }

    const sanitizeLastEntityBeforeQuery = (question) => {
      const le = conversationContext.value.lastEntity
      if (!le) return
      const n = le.name || ''
      const q = question
      const bio = /生平|逝世|去世|事迹|干过|什么时候|哪年|哪些事情|做过/.test(q)
      if (!bio || !isArtifactLikeName(n)) return
      const people = conversationContext.value.mentionedEntities.filter(
        (e) =>
          (e.type === '红色人物' || String(e.type || '').endsWith('人物')) &&
          !isArtifactLikeName(e.name)
      )
      if (people.length) {
        conversationContext.value.lastEntity = people[0]
      }
    }

    const collectAllNodeIdsForGraph = (response) => {
      const s = new Set()
      ;(response.entities || []).forEach((e) => {
        if (e && e.id != null) s.add(e.id)
      })
      collectAllEvidenceNodeIds(response.evidence_hits).forEach((id) => s.add(id))
      return [...s]
    }

    const syncContextFromResponse = (response, userQuestion) => {
      const fromApi = (response.entities || [])
        .filter((e) => e && e.id != null)
        .map((e) => ({ ...e }))
      const evHits = response.evidence_hits || []
      const seen = new Set(fromApi.map((e) => e.id))
      const fromEvidence = []
      collectAllEvidenceNodeIds(evHits).forEach((id) => {
        if (!seen.has(id)) {
          seen.add(id)
          fromEvidence.push({
            id,
            name: guessNameForNode(evHits, id),
            type: '未知'
          })
        }
      })
      const fromAnswer = [...fromApi, ...fromEvidence]
      if (fromAnswer.length) {
        const prev = conversationContext.value.lastEntity
        const focus = pickFocusEntityForTurn(fromAnswer, userQuestion, prev)
        conversationContext.value.lastEntity = focus || fromAnswer[0]
        conversationContext.value.mentionedEntities = mergeEntitiesById(
          conversationContext.value.mentionedEntities,
          fromAnswer
        )
      }
    }

    const onEvidenceClick = (ev) => {
      const nodeIds = extractNodeIdsFromEvidenceHit(ev)
      emit('focus-evidence', { nodeIds, hit: ev })
    }

    // 从消息中提取可能的实体
    const extractEntitiesFromMessage = (message) => {
      const entityKeywords = {
        '关向应': { id: 300, type: '红色人物' },
        '金伯阳': { id: 301, type: '红色人物' },
        '旅顺万忠墓': { id: 202, type: '红色场馆' },
        '关向应故居纪念馆': { id: 200, type: '红色场馆' },
        '大连中华工学会': { id: 201, type: '红色场馆' }
      }
      
      const mentioned = []
      for (const [keyword, entity] of Object.entries(entityKeywords)) {
        if (message.includes(keyword)) {
          mentioned.push(entity)
        }
      }
      return mentioned
    }

    // 构建带上下文的查询
    const buildContextQuery = (currentQuestion) => {
      let contextualizedQuery = currentQuestion

      const subject =
        conversationContext.value.lastEntity ||
        conversationContext.value.mentionedEntities[
          conversationContext.value.mentionedEntities.length - 1
        ]

      const entityName =
        subject &&
        (subject.name || subject.props?.名称 || subject.props?.实体名称 || '')

      const pronouns = ['他', '她', '它', '其', '这个', '那个', '这里', '那里']
      const hasPronoun = pronouns.some((p) => currentQuestion.includes(p))

      if (entityName && hasPronoun) {
        contextualizedQuery = currentQuestion.replace(/他|她|它|其|这个|那个/g, entityName)
        console.log('🔄 代词替换:', currentQuestion, '->', contextualizedQuery)
      }

      const followup =
        /什么|哪些|怎么|为何|为什么|干过|做过|事迹|生平|介绍|还有|另外|哪年|在哪|什么时候|多大|谁|如何/.test(
          currentQuestion
        )
      if (entityName && !currentQuestion.includes(entityName) && followup && !hasPronoun) {
        contextualizedQuery = `${entityName}${currentQuestion}`
        console.log('🔄 追问补全主语:', currentQuestion, '->', contextualizedQuery)
      }

      if (conversationContext.value.mentionedEntities.length > 0) {
        const contextInfo = conversationContext.value.mentionedEntities
          .map((e) => e.name || e.props?.名称)
          .filter(Boolean)
          .join('、')
        if (
          contextInfo &&
          !currentQuestion.includes(contextInfo) &&
          !entityName
        ) {
          contextualizedQuery = `关于${contextInfo}，${currentQuestion}`
        }
      }

      return contextualizedQuery
    }

    const sendMessage = async () => {
      if (!inputText.value.trim() || isLoading.value) return

      const question = inputText.value
      messages.value.push({
        type: 'user',
        content: question,
        evidence: []
      })
      inputText.value = ''

      isLoading.value = true

      try {
        const mentionedEntities = extractEntitiesFromMessage(question)
        if (mentionedEntities.length > 0) {
          conversationContext.value.lastEntity = mentionedEntities[0]
          conversationContext.value.mentionedEntities = mergeEntitiesById(
            conversationContext.value.mentionedEntities,
            mentionedEntities
          )
        }

        sanitizeLastEntityBeforeQuery(question)

        const contextualizedQuery = buildContextQuery(question)
        console.log('📤 发送带上下文的查询:', contextualizedQuery)
        console.log('📚 当前上下文:', conversationContext.value)

        const response = await askQuestion(contextualizedQuery, 12, conversationContext.value)
        console.log('📥 收到回答:', response)
        
        // 检查回答内容
        if (response.answer && response.answer.includes('无法回答')) {
          // 尝试用详情区的数据补充回答
          const enhancedAnswer = tryEnhanceAnswer(question, response)
          messages.value.push({
            type: 'assistant',
            content: enhancedAnswer || response.answer,
            evidence: response.evidence_hits || []
          })
        } else {
          messages.value.push({
            type: 'assistant',
            content: response.answer || '抱歉，没有找到相关信息',
            evidence: response.evidence_hits || []
          })
        }

        syncContextFromResponse(response, question)

        const nodeIds = collectAllNodeIdsForGraph(response)
        if (nodeIds.length > 0) {
          const idSet = new Set(nodeIds.map((x) => String(x)))
          let entity = conversationContext.value.lastEntity
          if (!entity || !idSet.has(String(entity.id))) {
            const entList = response.entities || []
            entity =
              entList.find((e) => e && idSet.has(String(e.id))) || {
                id: nodeIds[0],
                name: guessNameForNode(response.evidence_hits, nodeIds[0]),
                type: '未知'
              }
          }
          emit('select-entity', {
            entity,
            nodeIds
          })
        }
      } catch (error) {
        console.error('问答失败:', error)
        ElMessage.error('问答服务暂时不可用')
        messages.value.push({
          type: 'assistant',
          content: '抱歉，问答服务暂时不可用，请稍后再试。',
          evidence: []
        })
      } finally {
        isLoading.value = false
      }
    }

    // 尝试用详情区数据增强回答
    const tryEnhanceAnswer = (question, response) => {
      // 这里可以从当前选中的实体中获取信息
      // 或者从上下文中的 lastEntity 获取
      return null
    }

    return {
      messages,
      inputText,
      isLoading,
      userAvatar,
      botAvatar,
      sendMessage,
      conversationContext,
      onEvidenceClick
    }
  }
}
</script>

<style scoped>
.qa-chat {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 16px;
  padding-right: 8px;
}

.message {
  display: flex;
  margin-bottom: 16px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  margin: 0 8px;
  flex-shrink: 0;
}

.message-content {
  max-width: 70%;
}

.message-bubble {
  padding: 10px 14px;
  border-radius: 18px;
  background-color: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  white-space: pre-wrap;
  word-break: break-word;
}

.user .message-bubble {
  background-color: #409eff;
  color: white;
}

.message-evidence {
  margin-top: 8px;
  font-size: 12px;
}

.evidence-list {
  max-height: 220px;
  overflow-y: auto;
}

.evidence-item {
  background-color: #f0f2f5;
  padding: 6px 8px;
  border-radius: 4px;
  margin-top: 4px;
  color: #666;
  font-size: 11px;
  border-left: 2px solid #409eff;
}

.evidence-item--clickable {
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.evidence-item--clickable:hover {
  background-color: #e6f0ff;
  border-left-color: #66b1ff;
}

.evidence-item--clickable:focus {
  outline: 2px solid #409eff;
  outline-offset: 1px;
}

.chat-input {
  border-top: 1px solid #e4e7ed;
  padding-top: 16px;
}

.input-actions {
  margin-top: 8px;
  text-align: right;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background-color: white;
  border-radius: 18px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  width: fit-content;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background-color: #999;
  border-radius: 50%;
  animation: typing 1s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

/* 滚动条样式 */
.chat-history::-webkit-scrollbar {
  width: 6px;
}

.chat-history::-webkit-scrollbar-thumb {
  background-color: #ddd;
  border-radius: 3px;
}

.chat-history::-webkit-scrollbar-track {
  background-color: #f5f7fa;
}
</style>