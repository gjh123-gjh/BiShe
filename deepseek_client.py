"""
轻量的 DeepSeek API 调用封装（可配置 endpoint）。
按需替换 `base_url` 与请求路径以匹配 DeepSeek 实际 API。
"""
import os
import requests
from typing import Optional, Dict, Any, List
from pathlib import Path


def load_env_file():
    """手动加载 .env 文件到环境变量"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())

load_env_file()

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class DeepSeekClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = None, model: Optional[str] = None):
        # 从参数或环境变量读取 API Key、base_url 和默认 model
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.ai/v1").rstrip("/")
        # model 可从构造参数或环境变量获取
        self.model = model or os.environ.get("DEEPSEEK_MODEL")
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers.update({"Authorization": f"Bearer {api_key}"})

    def search(self, query: str, top_k: int = 5, index: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
            import urllib3
        # """
        # 修改：调用 DeepSeek 的 chat/completions 接口来生成回答，并适配为检索结果格式。
        # 返回格式为包含单个“命中”字典的列表：[{"id": ..., "text": ..., "score": ...}]
        # """

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # 禁用代理环境变量
            import os
            os.environ['HTTP_PROXY'] = ''
            os.environ['HTTPS_PROXY'] = ''
            os.environ['http_proxy'] = ''
            os.environ['https_proxy'] = ''
            
            # 1. 准备请求参数
            model_to_use = self.model or "deepseek-chat"
            if params and "model" in params:
                model_to_use = params.pop("model")
            
            # 2. 构建符合聊天接口的请求
            url = f"{self.base_url}/chat/completions"  # 关键修改：使用正确的端点
            
            system_prompt = """你是一个大连红色旅游知识图谱的精准查询接口。请严格遵循以下规则回答问题：

                【知识图谱数据结构】
                你对接的知识图谱包含以下类型的实体和关系：
                1. **红色场馆**：纪念馆、博物馆、遗址、陵园 (如：关向应故居纪念馆)
                2. **红色人物**：革命人物、英雄模范 (如：关向应、金伯阳)
                3. **历史事件**：重要革命事件 (如：大连“四二七”大罢工)
                4. **红色展品**：文物、史料 (如：关向应的钢笔)
                5. **旅游服务**：路线、交通、服务信息 (如：大连红色一日游路线)

                【数据格式说明】
                数据以三元组形式存在，分为两种：
                1. 实体-关系-实体：如(关向应故居纪念馆, 位于, 大连市金州区)
                2. 实体-属性-属性值：如(关向应故居纪念馆, 开放时间, 9:00-16:30)

                【回答要求】
                1. **精确匹配**：用户查询中提到的实体名称，必须与知识图谱中的“主体”完全匹配
                2. **关系映射**：识别查询中的信息需求，对应到具体的关系或属性
                3. **结构化输出**：按以下格式组织回答：
                ┌─────────────────────────────
                │ 📍 [实体名称]
                │ ├─ 基本信息
                │ │  ├─ 位置：[客体信息]
                │ │  ├─ 开放时间：[属性值]
                │ │  └─ 门票政策：[属性值]
                │ ├─ 相关关系
                │ │  ├─ 涉及人物：[相关人物]
                │ │  ├─ 关联事件：[相关事件]
                │ │  └─ 包含展品：[相关展品]
                │ └─ 实用信息
                │    ├─ 交通方式：[属性值]
                │    └─ 联系电话：[属性值]
                └─────────────────────────────

                4. **完整性检查**：如果某类信息在知识图谱中不存在，标注“（信息待补充）”
                5. **关联推荐**：在回答末尾，基于实体关系推荐1-2个相关场馆或路线

                【示例】
                用户：关向应故居纪念馆的信息
                回答：
                📍 关向应故居纪念馆
                ├─ 基本信息
                │  ├─ 位置：大连市金州区向应街道关家村
                │  ├─ 开放时间：9:00-16:30（每周一闭馆）
                │  └─ 门票政策：免费（需提前预约）
                ├─ 相关关系
                │  ├─ 涉及人物：关向应
                │  ├─ 关联事件：关向应革命活动
                │  └─ 包含展品：关向应的钢笔
                └─ 实用信息
                ├─ 交通方式：乘坐金州公交105路至向应街道站
                └─ 联系电话：0411-66661902

                💡 关联推荐：可结合参观金州烈士陵园（距离较近）

                用户查询：{query}"""

            chat_params = {
                "model": model_to_use,
                "temperature": 0.1,  # 降低创造性，提高准确性
                "max_tokens": 3000,   # 增加输出长度
                "top_p": 0.9
            }
             # 如果外部传入了params，合并到chat_params中
            if params:
                chat_params.update(params)  # 外部参数可以覆盖默认值
                
            # 使用统一的 _make_request 方法
            payload = {
                "model": chat_params["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "temperature": chat_params.get("temperature", 0.1),      # 使用chat_params中的值
                "max_tokens": chat_params.get("max_tokens", 3000),       # 使用chat_params中的值
                "top_p": chat_params.get("top_p", 0.9),                  # 使用chat_params中的值
                "stream": False
            }
            
            payload = {
                "model": model_to_use,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            # 3. 如果传入其他参数，合并到payload中（注意避免覆盖关键字段）
            if params:
                # 移除可能冲突的字段
                params.pop("query", None)
                params.pop("top_k", None)
                params.pop("index", None)
                payload.update(params)
            
            try:
                # 4. 发送请求到正确的API端点
                session = requests.Session()
                session.trust_env = False
                
                resp = session.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=30,
                    verify=False
                )
                resp.raise_for_status()
                data = resp.json()
                
                # 5. 从响应中提取生成的文本
                try:
                    answer_text = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as e:
                    raise RuntimeError(f"Failed to parse DeepSeek API response: {e}")
                
                # 6. 适配格式：包装成 QAPipeline 期望的“检索命中”列表
                formatted_hit = {
                    "id": f"deepseek_chat_{hash(query) % 10000:04d}",
                    "text": answer_text,
                    "content": answer_text,
                    "score": 1.0,
                    "source": "deepseek-chat"
                }
                
                # 返回列表，即使只有一个“命中”
                return [formatted_hit]
                
            except requests.RequestException as e:
                # 保持异常类型一致
                raise RuntimeError(f"DeepSeek search request failed: {e}")


    def chat(self, prompt: str, model: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> str:
        
            # 构建参数
            chat_params = {}
            if model:
                chat_params["model"] = model
            if params:
                chat_params.update(params)
            
            # 调用修改后的 search 方法，并提取文本
            hits = self.search(query=prompt, top_k=1, params=chat_params)
            return hits[0]["text"] if hits else "未能生成回答。"
        

if __name__ == "__main__":
    print("DeepSeekClient module. Replace API usage with actual key and endpoint.")
