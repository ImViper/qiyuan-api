# 自定义文件上传 API (Gemini)

本接口用于从 **运行 API 服务的服务器本地路径** 上传文件至 Gemini，并获取文件 URI 和使用的渠道 ID。

**警告:** 此接口直接读取服务器文件系统，存在安全风险。请确保已配置严格的路径访问限制，仅允许访问预先批准的安全目录。

## 端点信息

- **URL:** `/api/file/upload`
- **方法:** `POST`
- **认证:** 标准 API Key 认证 (通过 `Authorization` 请求头传递)
    ```
    Authorization: Bearer YOUR_API_KEY
    ```

## 请求

### 请求头

- `Authorization`: `Bearer <你的API密钥>`
- `Content-Type`: `application/json`

### 请求体 (JSON)

```json
{
  "local_path": "/path/on/the/server/to/your/file.mp3"
}
```

**参数说明:**

- `local_path` (string, **必需**): 文件在 **API 服务器** 上的绝对路径。**注意：** 只有在预先配置的允许目录下（例如 `H:\Code\jd_vedio`）的文件才能被访问。

## 响应

### 成功响应 (200 OK)

```json
{
  "uri": "files/xxxxxxxxxxx",
  "channel_id": 15
}
```

**参数说明:**

- `uri` (string): 文件成功上传到 Gemini 后返回的唯一标识符 (URI)。
- `channel_id` (integer): 本次上传实际使用的渠道 ID。**重要：** 后续如果需要在对话中引用此文件，**必须** 在请求中指定此 `channel_id`，以确保使用相同的 API 密钥进行访问。

### 错误响应

**400 Bad Request - 无效请求**

```json
{
  "error": {
    "message": "无效的请求体: invalid character '}' looking for beginning of object key string",
    "type": "invalid_request_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "请求体缺少 'local_path' 字段",
    "type": "invalid_request_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "无效的文件路径: stat /non/existent/path: no such file or directory",
    "type": "invalid_request_error"
  }
}
```

**403 Forbidden - 禁止访问**

```json
{
  "error": {
    "message": "禁止访问路径: /etc/passwd",
    "type": "invalid_request_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "无权访问本地文件 '/path/on/the/server/no_permission.txt'",
    "type": "invalid_request_error"
  }
}
```

**404 Not Found - 文件未找到**

```json
{
  "error": {
    "message": "本地文件 '/path/on/the/server/not_found.mp4' 未找到",
    "type": "invalid_request_error"
  }
}
```

**500 Internal Server Error - 服务器内部错误**

可能的原因包括：无法获取用户信息、无法获取有效的 Gemini 渠道、无法获取文件信息、上传到 Gemini 失败等。

```json
{
  "error": {
    "message": "获取用户信息失败: record not found",
    "type": "api_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "无法获取有效的 Gemini 渠道: XXXXX",
    "type": "api_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "上传文件到 Gemini 失败: XXXXX",
    "type": "api_error"
  }
}
```

## 使用示例 (cURL)

```bash
curl -X POST \
  http://YOUR_API_BASE_URL/api/file/upload \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "local_path": "H:/Code/jd_vedio/my_audio.mp3"
  }'
```

**请将 `YOUR_API_BASE_URL` 替换为你的 API 地址，将 `YOUR_API_KEY` 替换为有效的 API 密钥，并将 `local_path` 替换为服务器上实际存在且允许访问的文件路径。**

## 重要提示

1.  **服务器端路径:** `local_path` 指的是 **API 服务器** 上的文件路径，而不是调用方本地的路径。
2.  **安全限制:** 出于安全考虑，只有在服务器端预先配置的白名单目录下的文件才能被访问。
3.  **记录渠道 ID:** 文件上传成功后，务必记录响应中的 `channel_id`。
4.  **后续请求指定渠道 (管理员 & 特殊密钥格式):**
    *   当你需要在后续的 API 请求（例如使用文件进行图片理解或对话）中引用上传的文件时，**必须** 使用与上传时相同的渠道 ID，以确保 API 密钥一致。
    *   **当前系统的实现方式要求：**
        *   执行后续请求的用户必须拥有**管理员权限**。
        *   在后续请求的 `Authorization` 请求头中，API 密钥需要采用特殊格式：`Bearer <你的管理员Token>-<之前记录的channel_id>`。
        *   例如，如果你的管理员 Token 是 `sk-admin-secret`，文件上传时返回的 `channel_id` 是 `15`，那么后续请求的认证头应为：`Authorization: Bearer sk-admin-secret-15`。
    *   **注意：** 如果用户不是管理员，或者未使用此特殊密钥格式，系统将无法保证使用正确的渠道，可能导致访问文件失败或请求被拒绝。

# 批量上传文件 API (Gemini)

本接口用于从 **运行 API 服务的服务器本地路径** 批量上传多个文件至 Gemini，并获取每个文件的上传结果和使用的渠道 ID。

**警告:** 此接口直接读取服务器文件系统，存在安全风险。请确保已配置严格的路径访问限制，仅允许访问预先批准的安全目录。

## 端点信息

- **URL:** `/v1/files/batch-upload`
- **方法:** `POST`
- **认证:** 标准 API Key 认证 (通过 `Authorization` 请求头传递)
    ```
    Authorization: Bearer YOUR_API_KEY
    ```

## 请求

### 请求头

- `Authorization`: `Bearer <你的API密钥>`
- `Content-Type`: `application/json`

### 请求体 (JSON)

```json
{
  "local_paths": [
    "/path/on/the/server/to/your/file1.mp3",
    "/path/on/the/server/to/your/file2.jpg",
    "/path/on/the/server/to/your/file3.pdf"
  ]
}
```

**参数说明:**

- `local_paths` (array of strings, **必需**): 文件在 **API 服务器** 上的绝对路径列表。**注意：** 只有在预先配置的允许目录下（例如 `H:\Code\jd_vedio`）的文件才能被访问。

## 响应

### 成功响应 (200 OK)

```json
{
  "channel_id": 15,
  "results": [
    {
      "original_path": "/path/on/the/server/to/your/file1.mp3",
      "success": true,
      "file": {
        "name": "files/abc123",
        "displayName": "file1.mp3",
        "mimeType": "audio/mpeg",
        "sizeBytes": "12345",
        "createTime": "2025-05-01T12:34:56Z",
        "updateTime": "2025-05-01T12:34:56Z",
        "expirationTime": "2025-06-01T12:34:56Z",
        "sha256Hash": "hash_value",
        "uri": "files/abc123",
        "state": "ACTIVE"
      }
    },
    {
      "original_path": "/path/on/the/server/to/your/file2.jpg",
      "success": false,
      "error": "文件未找到"
    },
    {
      "original_path": "/path/on/the/server/to/your/file3.pdf",
      "success": true,
      "file": {
        "name": "files/def456",
        "displayName": "file3.pdf",
        "mimeType": "application/pdf",
        "sizeBytes": "67890",
        "createTime": "2025-05-02T10:11:12Z",
        "updateTime": "2025-05-02T10:11:12Z",
        "expirationTime": "2025-06-02T10:11:12Z",
        "sha256Hash": "hash_value",
        "uri": "files/def456",
        "state": "ACTIVE"
      }
    }
  ]
}
```

**参数说明:**

- `channel_id` (integer): 本次上传实际使用的渠道 ID。**重要：** 后续如果需要在对话中引用这些文件，**必须** 在请求中指定此 `channel_id`，以确保使用相同的 API 密钥进行访问。
- `results` (array): 包含所有上传结果的数组，每个元素对应一个文件的上传结果：
  - `original_path` (string): 原始请求中的文件路径。
  - `success` (boolean): 表示此文件是否上传成功。
  - 对于成功上传的文件，包含 `file` 对象，其中包含文件的详细信息：
    - `name` (string): 文件的完整 ID。
    - `displayName` (string): 文件的显示名称。
    - `mimeType` (string): 文件的 MIME 类型。
    - `sizeBytes` (string): 文件大小（字节）。
    - `createTime` (string): 文件创建时间。
    - `updateTime` (string): 文件最后更新时间。
    - `expirationTime` (string): 文件过期时间。
    - `sha256Hash` (string): 文件的 SHA-256 哈希值。
    - `uri` (string): 文件的 URI。
    - `state` (string): 文件的当前状态。
  - 对于上传失败的文件，包含 `error` 字段，说明错误原因。

### 错误响应

**400 Bad Request - 无效请求**

```json
{
  "error": {
    "message": "无效的请求体: invalid character '}' looking for beginning of object key string",
    "type": "invalid_request_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "请求体缺少有效的 'local_paths' 字段或为空数组",
    "type": "invalid_request_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "无效的文件路径 '/non/existent/path': no such file or directory",
    "type": "invalid_request_error"
  }
}
```

**403 Forbidden - 禁止访问**

```json
{
  "error": {
    "message": "禁止访问路径: /etc/passwd",
    "type": "invalid_request_error"
  }
}
```

**500 Internal Server Error - 服务器内部错误**

可能的原因包括：无法获取用户信息、无法获取有效的 Gemini 渠道等。

```json
{
  "error": {
    "message": "获取用户信息失败: record not found",
    "type": "api_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "无法获取有效的 Gemini 渠道: XXXXX",
    "type": "api_error"
  }
}
```

## 使用示例 (cURL)

```bash
curl -X POST \
  http://YOUR_API_BASE_URL/v1/files/batch-upload \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "local_paths": [
      "H:/Code/jd_vedio/file1.mp3",
      "H:/Code/jd_vedio/file2.jpg",
      "H:/Code/jd_vedio/file3.pdf"
    ]
  }'
```

**请将 `YOUR_API_BASE_URL` 替换为你的 API 地址，将 `YOUR_API_KEY` 替换为有效的 API 密钥，并将 `local_paths` 数组中的路径替换为服务器上实际存在且允许访问的文件路径。**

## 重要提示

1. **并发上传:** 该接口内部实现了并发上传，默认并发数为5，可以高效地处理多个文件。
2. **渠道一致性:** 所有文件使用相同的渠道进行上传，确保API密钥一致性。
3. **服务器端路径:** `local_paths` 中的路径指的是 **API 服务器** 上的文件路径，而不是调用方本地的路径。
4. **安全限制:** 出于安全考虑，只有在服务器端预先配置的白名单目录下的文件才能被访问。
5. **错误处理:** 即使部分文件上传失败，接口仍会返回成功状态码 (200)，并在结果中标明每个文件的成功或失败状态。

# 批量查询文件状态 API (Gemini)

本接口用于批量查询多个 Gemini 文件的状态信息，避免一个一个单独查询。

## 端点信息

- **URL:** `/v1/files/batch-status`
- **方法:** `POST`
- **认证:** 标准 API Key 认证 (通过 `Authorization` 请求头传递)
    ```
    Authorization: Bearer YOUR_API_KEY
    ```

## 请求

### 请求头

- `Authorization`: `Bearer <你的API密钥>`
- `Content-Type`: `application/json`

### 请求体 (JSON)

```json
{
  "file_names": [
    "files/abc123",
    "files/def456",
    "files/ghi789"
  ]
}
```

**参数说明:**

- `file_names` (array of strings, **必需**): 要查询的文件 ID 列表。每个 ID 通常以 `files/` 开头，后跟文件的唯一标识符。

## 响应

### 成功响应 (200 OK)

```json
{
  "results": {
    "files/abc123": {
      "file": {
        "name": "files/abc123",
        "displayName": "example.jpg",
        "mimeType": "image/jpeg",
        "sizeBytes": "12345",
        "createTime": "2025-05-01T12:34:56Z",
        "updateTime": "2025-05-01T12:34:56Z",
        "expirationTime": "2025-06-01T12:34:56Z",
        "sha256Hash": "hash_value",
        "uri": "files/abc123",
        "state": "ACTIVE"
      }
    },
    "files/def456": {
      "error": "File not found"
    },
    "files/ghi789": {
      "file": {
        "name": "files/ghi789",
        "displayName": "document.pdf",
        "mimeType": "application/pdf",
        "sizeBytes": "67890",
        "createTime": "2025-05-02T10:11:12Z",
        "updateTime": "2025-05-02T10:11:12Z",
        "expirationTime": "2025-06-02T10:11:12Z",
        "sha256Hash": "hash_value",
        "uri": "files/ghi789",
        "state": "PROCESSING"
      }
    }
  }
}
```

**参数说明:**

- `results` (object): 包含所有查询结果的映射，键是文件 ID，值是查询结果。
  - 对于成功查询的文件，结果包含 `file` 对象，其中包含文件的详细信息：
    - `name` (string): 文件的完整 ID。
    - `displayName` (string): 文件的显示名称。
    - `mimeType` (string): 文件的 MIME 类型。
    - `sizeBytes` (string): 文件大小（字节）。
    - `createTime` (string): 文件创建时间。
    - `updateTime` (string): 文件最后更新时间。
    - `expirationTime` (string): 文件过期时间。
    - `sha256Hash` (string): 文件的 SHA-256 哈希值。
    - `uri` (string): 文件的 URI。
    - `state` (string): 文件的当前状态，可能的值包括：
      - `ACTIVE`: 文件已处理完成，可以使用。
      - `PROCESSING`: 文件正在处理中。
      - `FAILED`: 文件处理失败。
  - 对于查询失败的文件，结果包含 `error` 字段，说明错误原因。

### 错误响应

**400 Bad Request - 无效请求**

```json
{
  "error": {
    "message": "无效的请求体: invalid character '}' looking for beginning of object key string",
    "type": "invalid_request_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "请求体缺少有效的 'file_names' 字段或为空数组",
    "type": "invalid_request_error"
  }
}
```

**500 Internal Server Error - 服务器内部错误**

可能的原因包括：无法获取用户信息、无法获取有效的 Gemini 渠道等。

```json
{
  "error": {
    "message": "获取用户信息失败: record not found",
    "type": "api_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "无法获取有效的 Gemini 渠道: XXXXX",
    "type": "api_error"
  }
}
```
*或*
```json
{
  "error": {
    "message": "批量查询文件状态失败: XXXXX",
    "type": "api_error"
  }
}
```

## 使用示例 (cURL)

```bash
curl -X POST \
  http://YOUR_API_BASE_URL/v1/files/batch-status \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "file_names": [
      "files/abc123",
      "files/def456",
      "files/ghi789"
    ]
  }'
```

**请将 `YOUR_API_BASE_URL` 替换为你的 API 地址，将 `YOUR_API_KEY` 替换为有效的 API 密钥，并将 `file_names` 数组中的值替换为你要查询的实际文件 ID。**

## 重要提示

1. **并发查询:** 该接口内部实现了并发查询，可以高效地处理大量文件 ID。
2. **渠道一致性:** 与文件上传类似，确保使用与上传文件时相同的渠道 ID 进行查询。
3. **文件状态:** 注意检查返回的文件 `state` 字段，只有 `ACTIVE` 状态的文件才能被正常使用。
4. **错误处理:** 即使部分文件查询失败，接口仍会返回成功状态码 (200)，并在结果中标明每个文件的成功或失败状态。
