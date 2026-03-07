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
            <div v-for="(ev, idx) in message.evidence.slice(0, 3)" :key="idx" class="evidence-item">
              {{ ev.text }}
            </div>
            <div v-if="message.evidence.length > 3" class="more-evidence">
              等 {{ message.evidence.length }} 条证据
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
  emits: ['select-entity', 'update-context'],
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
      
      // 如果当前问题包含代词，尝试用上下文补充
      const pronouns = ['他', '她', '它', '其', '这个', '那个', '这里', '那里']
      const hasPronoun = pronouns.some(p => currentQuestion.includes(p))
      
      if (hasPronoun && conversationContext.value.lastEntity) {
        // 替换代词为具体的实体名称
        const entityName = conversationContext.value.lastEntity.name || 
                          conversationContext.value.lastEntity.props?.名称 || 
                          '该实体'
        contextualizedQuery = currentQuestion.replace(
          /他|她|它|其|这个|那个/g, 
          entityName
        )
        console.log('🔄 代词替换:', currentQuestion, '->', contextualizedQuery)
      }
      
      // 添加历史上下文信息
      if (conversationContext.value.mentionedEntities.length > 0) {
        const contextInfo = conversationContext.value.mentionedEntities
          .map(e => e.name || e.props?.名称)
          .filter(Boolean)
          .join('、')
        
        if (contextInfo && !currentQuestion.includes(contextInfo)) {
          contextualizedQuery = `关于${contextInfo}，${currentQuestion}`
        }
      }
      
      return contextualizedQuery
    }

// 在 QAChat.vue 中修改 sendMessage 函数

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
        // 从当前问题提取实体
        const mentionedEntities = extractEntitiesFromMessage(question)
        
        // 更新上下文
        if (mentionedEntities.length > 0) {
          conversationContext.value.lastEntity = mentionedEntities[0]
          conversationContext.value.mentionedEntities = [
            ...new Set([...conversationContext.value.mentionedEntities, ...mentionedEntities])
          ]
        }
        
        // 构建带上下文的查询
        const contextualizedQuery = buildContextQuery(question)
        console.log('📤 发送带上下文的查询:', contextualizedQuery)
        console.log('📚 当前上下文:', conversationContext.value)
        
        // 发送到后端，同时传递上下文
        const response = await askQuestion(contextualizedQuery, 5, conversationContext.value)
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

        // 如果有实体，触发选择事件
        if (response.entities && response.entities.length > 0) {
          const nodeIds = response.entities.map(e => e.id)
          emit('select-entity', response.entities[0], nodeIds)
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
      conversationContext
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

.evidence-item {
  background-color: #f0f2f5;
  padding: 6px 8px;
  border-radius: 4px;
  margin-top: 4px;
  color: #666;
  font-size: 11px;
  border-left: 2px solid #409eff;
}

.more-evidence {
  text-align: right;
  color: #999;
  font-size: 11px;
  margin-top: 2px;
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