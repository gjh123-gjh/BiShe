说明：DeepSeek 调用与基于检索的问答（RAG）示例

- 目标：使用 DeepSeek 做向量检索，把检索到的文档拼接成证据，再交给 LLM 生成基于证据的回答。

快速上手
1. 安装依赖：

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

2. 设置环境变量：

- `DEEPSEEK_API_KEY`：DeepSeek 的 API Key（若需要）。
- `DEEPSEEK_BASE_URL`：可选，自定义 DeepSeek endpoint（默认示例里为 https://api.deepseek.ai/v1）。

3. 示例运行：

```bash
python qa_pipeline.py
```

替换 LLM：
- 编辑 `qa_pipeline.py` 中示例的 `demo_llm_fn`，用你的 LLM 调用包装替换它（OpenAI、Azure、或自托管 LLM）。

注意事项
- DeepSeek API 的实际请求格式可能与示例不同，请根据官方文档调整 `deepseek_client.py` 中的 `search` 方法的 `url` 与 `payload`。
- 生产环境请为 HTTP 调用添加重试、超时与限流机制。