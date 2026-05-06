<script setup>
import { ref, onMounted, nextTick, computed } from 'vue';
import axios from 'axios';
import { marked } from 'marked';
import { 
  SendHorizontal, 
  User, 
  Bot, 
  Loader2, 
  Eraser, 
  ChevronRight,
  MapPin,
  Calendar,
  Phone,
  Bookmark
} from 'lucide-vue-next';

// --- 状态管理 ---
const query = ref('');
const messages = ref([
  {
    role: 'bot',
    content: '您好！我是大连红色旅游智能助手。您可以问我关于大连红色场馆、革命人物、历史事件或旅游建议的问题。',
    timestamp: new Date().toLocaleTimeString(),
    evidence: []
  }
]);
const isLoading = ref(false);
const chatContainer = ref(null);
const currentContext = ref({});

// --- API 配置 ---
const API_BASE = 'http://localhost:5000/api/qa/ask';

// --- Markdown 配置 ---
marked.setOptions({
  breaks: true,
  gfm: true
});

// --- 辅助函数 ---
const scrollToBottom = async () => {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTo({
      top: chatContainer.value.scrollHeight,
      behavior: 'smooth'
    });
  }
};

const formatContent = (content) => {
  return marked.parse(content);
};

// --- 核心业务逻辑 ---
const sendMessage = async () => {
  if (!query.value.trim() || isLoading.value) return;

  const userQuery = query.value.trim();
  messages.value.push({
    role: 'user',
    content: userQuery,
    timestamp: new Date().toLocaleTimeString()
  });
  
  query.value = '';
  isLoading.value = true;
  await scrollToBottom();

  try {
    const response = await axios.post(API_BASE, {
      query: userQuery,
      context: currentContext.value
    });

    const data = response.data;
    
    // 更新上下文（保存最后提到的实体，以便追问）
    if (data.entities && data.entities.length > 0) {
      currentContext.value.lastEntity = data.entities[0];
    }

    messages.value.push({
      role: 'bot',
      content: data.answer || '抱歉，我未能生成有效的回答。',
      timestamp: new Date().toLocaleTimeString(),
      evidence: data.evidence_hits || [],
      entities: data.entities || []
    });
  } catch (error) {
    console.error('发送失败:', error);
    messages.value.push({
      role: 'bot',
      content: '❌ **网络连接失败**：请确保后端服务 (Flask) 已启动。',
      timestamp: new Date().toLocaleTimeString(),
      isError: true
    });
  } finally {
    isLoading.value = false;
    await scrollToBottom();
  }
};

const clearChat = () => {
  messages.value = [messages.value[0]];
  currentContext.value = {};
};

// --- 初始化 ---
onMounted(() => {
  scrollToBottom();
});
</script>

<template>
  <div class="flex flex-col h-screen bg-background text-gray-800">
    <!-- Header -->
    <header class="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-gray-200">
      <div class="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-lg transform rotate-3">
            <Bookmark class="text-white w-6 h-6" />
          </div>
          <div>
            <h1 class="text-xl font-bold tracking-tight text-gray-900 leading-none">大连红色旅游</h1>
            <span class="text-xs font-semibold text-primary uppercase tracking-widest">智能问答系统</span>
          </div>
        </div>
        <button 
          @click="clearChat"
          class="p-2 text-gray-400 hover:text-primary transition-colors duration-200"
          title="清空记录"
        >
          <Eraser class="w-5 h-5" />
        </button>
      </div>
    </header>

    <!-- Chat Body -->
    <main 
      ref="chatContainer"
      class="flex-1 overflow-y-auto px-4 py-8 no-scrollbar"
    >
      <div class="max-w-3xl mx-auto space-y-8">
        <div 
          v-for="(msg, index) in messages" 
          :key="index"
          class="flex"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div 
            class="flex gap-4 group"
            :class="msg.role === 'user' ? 'flex-row-reverse max-w-[85%]' : 'flex-row max-w-[90%]'"
          >
            <!-- Avatar -->
            <div 
              class="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-transform group-hover:scale-110 shadow-sm"
              :class="msg.role === 'user' ? 'bg-primary text-white' : 'bg-white border border-gray-100 text-primary'"
            >
              <User v-if="msg.role === 'user'" class="w-5 h-5" />
              <Bot v-else class="w-5 h-5" />
            </div>

            <!-- Content -->
            <div class="space-y-2">
              <div 
                class="px-4 py-3 rounded-2xl shadow-sm leading-relaxed text-[15px]"
                :class="[
                  msg.role === 'user' 
                    ? 'bg-red-50 text-primary-dark border border-red-100 rounded-tr-none' 
                    : 'bg-white text-gray-700 border border-gray-100 rounded-tl-none',
                  msg.isError ? 'border-red-200 bg-red-50' : ''
                ]"
              >
                <!-- BOT 回答解析 Markdown -->
                <div 
                  v-if="msg.role === 'bot'"
                  class="markdown-body prose prose-slate max-w-none prose-p:my-1 prose-headings:mb-2 prose-headings:mt-4"
                  v-html="formatContent(msg.content)"
                ></div>
                
                <!-- USER 原文 -->
                <div v-else class="whitespace-pre-wrap">
                  {{ msg.content }}
                </div>
              </div>
              
              <!-- Evidence Chips -->
              <div 
                v-if="msg.evidence && msg.evidence.length > 0"
                class="flex flex-wrap gap-2 pt-1"
              >
                <div 
                  v-for="hit in msg.evidence.slice(0, 3)" 
                  :key="hit.id"
                  class="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full border border-gray-200"
                >
                  证: {{ hit.id }}
                </div>
              </div>

              <!-- Timestamp -->
              <p class="text-[10px] text-gray-300 mx-1" :class="msg.role === 'user' ? 'text-right' : 'text-left'">
                {{ msg.timestamp }}
              </p>
            </div>
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading" class="flex justify-start">
          <div class="flex flex-row max-w-[90%] gap-4">
            <div class="flex-shrink-0 w-9 h-9 rounded-lg bg-white border border-gray-100 text-primary flex items-center justify-center">
              <Loader2 class="w-5 h-5 animate-spin" />
            </div>
            <div class="bg-white border border-gray-100 px-4 py-3 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-3">
              <div class="flex space-x-1">
                <div class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce"></div>
                <div class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              </div>
              <span class="text-xs text-gray-400 font-medium">正在寻求专家解答...</span>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Footer Input -->
    <footer class="p-6 bg-transparent">
      <div class="max-w-3xl mx-auto relative group">
        <!-- Input Overlay Decoration -->
        <div class="absolute -inset-1 bg-gradient-to-r from-primary/10 to-transparent rounded-3xl blur opacity-25 group-focus-within:opacity-50 transition duration-1000 group-hover:duration-200"></div>
        
        <div class="relative flex items-center bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden focus-within:border-primary/30 transition-all duration-300 translate-y-0 focus-within:-translate-y-1">
          <input 
            v-model="query"
            @keyup.enter="sendMessage"
            type="text"
            placeholder="输入您想了解的大连红色旅游问题..."
            class="flex-1 px-5 py-4 bg-transparent outline-none text-gray-700 placeholder-gray-400 text-sm"
          />
          <div class="pr-2">
            <button 
              @keyup.enter="sendMessage"
              @click="sendMessage"
              :disabled="!query.trim() || isLoading"
              class="p-3 rounded-xl transition-all duration-300"
              :class="query.trim() && !isLoading ? 'bg-primary text-white shadow-md hover:bg-primary-dark cursor-pointer' : 'bg-gray-50 text-gray-300 cursor-not-allowed'"
            >
              <SendHorizontal class="w-5 h-5" />
            </button>
          </div>
        </div>
        
        <!-- Suggestions/Quick Links -->
        <div class="mt-4 flex flex-wrap gap-2 justify-center pb-2">
          <p class="text-[11px] text-gray-400 w-full text-center mb-1">您也可以试着问问这些热门话题：</p>
          <button 
            v-for="tag in ['关向应的历史事迹', '推荐一条一日游路线', '大连中华工学会旧址在哪']"
            :key="tag"
            @click="query = tag"
            class="text-[11px] px-3 py-1.5 bg-white border border-gray-100 rounded-full text-gray-500 hover:border-primary/30 hover:text-primary transition-all duration-200 shadow-sm"
          >
            {{ tag }}
          </button>
        </div>
      </div>
    </footer>
  </div>
</template>

<style>
/* Markdown 样式修饰 */
.markdown-body h1, .markdown-body h2, .markdown-body h3 { border-bottom: none; color: #111827; }
.markdown-body ul { list-style-type: disc; margin-left: 1.25rem; }
.markdown-body strong { color: #D32F2F; font-weight: 700; }
.markdown-body code { background: #f3f4f6; padding: 0.125rem 0.25rem; border-radius: 0.25rem; font-size: 0.875em; }

/* 响应式调整 */
@media (max-width: 640px) {
  .prose { font-size: 0.875rem; }
}
</style>
