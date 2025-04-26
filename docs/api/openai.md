OpenAI 对话格式（Chat Completions）¶
官方文档

OpenAI Chat

📝 简介¶
给定一组包含对话的消息列表，模型将返回一个响应。相关指南可参阅OpenAI官网：Chat Completions

💡 请求示例¶
基础文本对话 ✅¶

curl https://newapi地址/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NEWAPI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "system",
        "content": "你是一个有帮助的助手。"
      },
      {
        "role": "user",
        "content": "你好!"
      }
    ]
  }'
响应示例:


{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o-mini",
  "system_fingerprint": "fp_44709d6fcb",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "你好!我很高兴能帮助你。请问有什么我可以协助你的吗?"
    },
    "logprobs": null,
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
图像分析对话 ✅¶

curl https://newapi地址/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NEWAPI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "这张图片里有什么?"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "https://example.com/image.jpg"
            }
          }
        ]
      }
    ],
    "max_tokens": 300
  }'
响应示例:


{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o-mini",
  "system_fingerprint": "fp_44709d6fcb",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "这张图片展示了一条木制栈道穿过茂密的绿色湿地。栈道似乎延伸到远处,两旁是郁郁葱葱的植被。"
    },
    "logprobs": null,
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
流式响应 ✅¶

curl https://newapi地址/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NEWAPI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": "讲个故事"
      }
    ],
    "stream": true
  }'
流式响应示例:


{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini","system_fingerprint":"fp_44709d6fcb","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}

{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini","system_fingerprint":"fp_44709d6fcb","choices":[{"index":0,"delta":{"content":"从前"},"logprobs":null,"finish_reason":null}]}

{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini","system_fingerprint":"fp_44709d6fcb","choices":[{"index":0,"delta":{"content":"有一只"},"logprobs":null,"finish_reason":null}]}

{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini","system_fingerprint":"fp_44709d6fcb","choices":[{"index":0,"delta":{"content":"小兔子"},"logprobs":null,"finish_reason":null}]}

// ... 更多数据块 ...

{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini","system_fingerprint":"fp_44709d6fcb","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}]}
函数调用 ✅¶

curl https://newapi地址/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NEWAPI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": "北京今天的天气怎么样?"
      }
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "获取指定位置的当前天气",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "城市名称,如: 北京"
              },
              "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"]
              }
            },
            "required": ["location"]
          }
        }
      }
    ],
    "tool_choice": "auto"
  }'
响应示例:


{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1699896916,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"北京\", \"unit\": \"celsius\"}"
            }
          }
        ]
      },
      "logprobs": null,
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 82,
    "completion_tokens": 17,
    "total_tokens": 99
  }
}
JSON 模式输出 ✅¶

curl https://newapi地址/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NEWAPI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "system",
        "content": "你是一个JSON助手,请以JSON格式回复。"
      },
      {
        "role": "user",
        "content": "给我一个用户信息示例"
      }
    ],
    "response_format": { "type": "json_object" }
  }'
响应示例:


{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o-mini",
  "system_fingerprint": "fp_44709d6fcb",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "{\"user\":{\"id\":1,\"name\":\"张三\",\"age\":28,\"email\":\"zhangsan@example.com\",\"interests\":[\"读书\",\"旅游\",\"摄影\"]}}"
    },
    "logprobs": null,
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
📮 请求¶
端点¶

POST /v1/chat/completions
创建给定聊天对话的模型响应。更多详情请参阅文本生成、视觉和音频指南。

鉴权方法¶
在请求头中包含以下内容进行 API 密钥认证：


Authorization: Bearer $NEWAPI_API_KEY
其中 $NEWAPI_API_KEY 是您的 API 密钥。您可以在 OpenAI 平台的 API 密钥页面中找到或生成 API 密钥。

请求体参数¶
messages¶
类型：数组
必需：是
到目前为止包含对话的消息列表。根据使用的模型，支持不同的消息类型（形式），如文本、图像和音频。

model¶
类型：字符串
必需：是
要使用的模型 ID。有关哪些模型适用于 Chat API 的详细信息，请参阅模型端点兼容性表。

store¶
类型：布尔值或 null
必需：否
默认值：false
是否存储此聊天补全请求的输出以用于我们的模型蒸馏或评估产品。

reasoning_effort¶
类型：字符串或 null
必需：否
默认值：medium
仅适用于 o1 和 o3-mini 模型
约束推理模型的推理工作。当前支持的值为 low、medium 和 high。减少推理工作可以加快响应速度并减少响应中用于推理的标记数。

metadata¶
类型：map
必需：否
可以附加到对象的16个键值对集合。这对于以结构化格式存储对象的其他信息很有用,并可以通过 API 或仪表板查询对象。

键是最大长度为64个字符的字符串。值是最大长度为512个字符的字符串。

modalities¶
类型：数组或 null
必需：否
您希望模型为此请求生成的输出类型。大多数模型都能生成文本,这是默认设置: ["text"]

该模型还可以用于生成音频。要请求此模型同时生成文本和音频响应,您可以使用: ["text", "audio"]

prediction¶
类型：对象
必需：否
预测输出的配置,当提前知道模型响应的大部分内容时,可以大大提高响应时间。这在您只对文件进行微小更改时最常见。

audio¶
类型：对象或 null
必需：否
音频输出的参数。当使用 modalities: ["audio"] 请求音频输出时需要。

temperature¶
类型：数字或 null
必需：否
默认值：1
要使用的采样温度，介于 0 和 2 之间。较高的值（如0.8）会使输出更加随机，而较低的值（如0.2）会使其更加集中和确定性。我们通常建议更改此值或 top_p，但不要同时更改。

top_p¶
类型：数字或 null
必需：否
默认值：1
一种替代采样温度的方法，称为核采样，其中模型考虑具有 top_p 概率质量的标记结果。因此，0.1 意味着只考虑包含前 10% 概率质量的标记。

我们通常建议更改此值或 temperature，但不要同时更改。

n¶
类型：整数或 null
必需：否
默认值：1
为每个输入消息生成多少个聊天补全选择。请注意，您将根据所有选择生成的标记数量收费。保持 n 为 1 可最大限度地降低成本。

stop¶
类型：字符串/数组/null
必需：否
默认值：null
API 将停止生成更多标记的最多 4 个序列。

max_tokens¶
类型：整数或 null
必需：否
聊天补全中可以生成的最大标记数。此值可用于控制通过 API 生成的文本成本。

该值现已弃用，取而代之的是 max_completion_tokens，并且与 o1 系列模型不兼容。

presence_penalty¶
类型：数字或 null
必需：否
默认值：0
介于 -2.0 和 2.0 之间的数字。正值根据新标记到目前为止在文本中出现的情况来惩罚它们，从而增加模型讨论新主题的可能性。

frequency_penalty¶
类型：数字或 null
必需：否
默认值：0
介于 -2.0 和 2.0 之间的数字。正值根据新标记到目前为止在文本中的现有频率来惩罚它们，从而降低模型逐字重复同一行的可能性。

logit_bias¶
类型：map
必需：否
默认值：null
修改指定标记出现在补全中的可能性。

接受一个 JSON 对象，该对象将标记（由分词器中的标记 ID 指定）映射到从 -100 到 100 的关联偏差值。在数学上，偏差被添加到模型在采样之前生成的对数中。确切的效果会因模型而异，但介于 -1 和 1 之间的值应该会减少或增加选择的可能性；像 -100 或 100 这样的值应该导致相关标记被禁止或独占选择。

user¶
类型：字符串
必需：否
表示最终用户的唯一标识符，可以帮助 OpenAI 监控和检测滥用行为。了解更多。

service_tier¶
类型：字符串或 null
必需：否
默认值：auto
指定用于处理请求的延迟层级。此参数与订阅了 scale tier 服务的客户相关：

如果设置为 'auto'，且项目启用了 Scale tier，系统将使用 scale tier 信用直到用完
如果设置为 'auto'，且项目未启用 Scale tier，请求将使用默认服务层级处理，具有较低的正常运行时间 SLA 且无延迟保证
如果设置为 'default'，请求将使用默认服务层级处理，具有较低的正常运行时间 SLA 且无延迟保证
未设置时，默认行为为 'auto'
stream_options¶
类型：对象或 null
必需：否
默认值：null
流式响应的选项。仅在设置 stream: true 时使用。

response_format¶
类型：对象
必需：否
指定模型必须输出的格式。

设置为 { "type": "json_schema", "json_schema": {...} } 启用结构化输出，确保模型将匹配您提供的 JSON schema。
设置为 { "type": "json_object" } 启用 JSON 模式，确保模型生成的消息是有效的 JSON。
重要提示：使用 JSON 模式时，您还必须通过系统或用户消息自行指示模型生成 JSON。否则，模型可能会生成无尽的空白直到生成达到令牌限制。

seed¶
类型：整数或 null
必需：否
Beta 功能。如果指定，我们的系统将尽最大努力进行确定性采样，使得具有相同 seed 和参数的重复请求应返回相同的结果。不保证确定性，您应参考响应参数以监控后端的变化。

tools¶
类型：数组
必需：否
模型可能调用的工具列表。目前仅支持函数作为工具。使用此参数提供模型可能生成 JSON 输入的函数列表。最多支持 128 个函数。

tool_choice¶
类型：字符串或对象
必需：否
控制模型调用哪个工具（如果有）： - none：模型不会调用任何工具，而是生成消息 - auto：模型可以在生成消息或调用一个或多个工具之间选择 - required：模型必须调用一个或多个工具 - {"type": "function", "function": {"name": "my_function"}}：强制模型调用特定工具

当没有工具时默认为 none，有工具时默认为 auto。

parallel_tool_calls¶
类型：布尔值
必需：否
默认值：true
是否在工具使用期间启用并行函数调用。

📥 响应¶
成功响应¶
返回一个聊天补全对象,如果请求被流式传输,则返回聊天补全块对象的流式序列。

id¶
类型：字符串
说明：响应的唯一标识符
object¶
类型：字符串
说明：对象类型,值为 "chat.completion"
created¶
类型：整数
说明：响应创建时间戳
model¶
类型：字符串
说明：使用的模型名称
system_fingerprint¶
类型：字符串
说明：系统指纹标识符
choices¶
类型：数组
说明：包含生成的回复选项
属性:
index: 选项索引
message: 包含角色和内容的消息对象
logprobs: 日志概率信息
finish_reason: 完成原因
usage¶
类型：对象
说明：token 使用统计
属性:
prompt_tokens: 提示使用的 token 数
completion_tokens: 补全使用的 token 数
total_tokens: 总 token 数
completion_tokens_details: token 详细信息