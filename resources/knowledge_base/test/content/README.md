# hw-chat
hw-chat 项目的后端服务，负责处理业务逻辑、数据存储和API接口的提供。采用稳健的后端技术，确保服务的稳定性和可扩展性。

## 使用示例

使用 Postman 或其他 HTTP 客户端工具访问 API 接口：

### POST 请求示例

```http
http://localhost:6006/api/chat/knowledge_base_chat

{
    "query":"什么是GLM4 多角色对话",
    "user_id":"admin",
    "conversation_id": "df221b2f-ea52-4200-82f5-fcfc011e6786", 
    "conversation_name":"新对话",
    "knowledge_base_name":"private",
    "top_k":"3",
    "score_threshold":"0.5",
    "history":[],
    "history_len": 3,
    "stream": false,
    "model_name":"chatglm3-6b",
    "prompt_name":"default"
}
```

<table><thead><tr><th>No.</th><th>Description</th><th>Qty</th><th>UM</th><th>Net price</th><th>Net worth</th><th>VAT [%]</th><th>Gross 
worth</th></tr></thead><tbody><tr><td></td><td>人 工 智能</td><td>5,00</td><td>eacn</td><td>12,00</td><td>60,00</td><td>109%</td><td>66,00</td></tr><tr><td></td><td>机 器 学 
习</td><td>4,00</td><td>eacn</td><td>28,08</td><td>112,32</td><td>109%</td><td>123,55</td></tr><tr><td></td><td>大 模型 
技术</td><td>1,00</td><td>eacn</td><td>7,50</td><td>7,50</td><td>109%</td><td>8,25</td></tr><tr><td></td><td>自然 语言 处 
理</td><td>1,00</td><td>eacn</td><td>12,99</td><td>12,99</td><td>109%</td><td>14,29</td></tr></tbody></table>

SUMMARY

<table><thead><tr><th>VAT</th><th>[%]</th><th>Net worth</th><th>VAT</th><th>Gross 
worth</th></tr></thead><tbody><tr><td>109%</td><td></td><td>192,81</td><td>19,28</td><td>212,09</td></tr><tr><td colspan="2">Total</td><td>中 192,81</td><td>向 19,28</td><td>下 
212,09</td></tr></tbody></table>
