// src/main.js
cat > src/main.js << 'EOF'
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from 'D:\BiShe\red-tourism-vue\src\App.vue'

const app = createApp(App)
app.use(ElementPlus)
app.mount('#app')
EOF