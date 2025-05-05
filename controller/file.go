package controller

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/gin-gonic/gin"
	"google.golang.org/genai"
	"one-api/model"
	"one-api/relay/channel/gemini"
	"one-api/relay/common"
)

// Request body structure for local file upload
type UploadLocalFileRequest struct {
	LocalPath string `json:"local_path"`
}

// BatchFileStatusRequest 批量查询文件状态的请求结构
type BatchFileStatusRequest struct {
	FileNames []string `json:"file_names"` // 文件名称列表，例如 ["files/id1", "files/id2"]
}

// BatchUploadFileRequest 批量上传文件的请求结构
type BatchUploadFileRequest struct {
	LocalPaths []string `json:"local_paths"` // 本地文件路径列表
}

// UploadFile handles file uploads from a local server path for Gemini.
// !!! WARNING: This function reads files from the local server path specified
// !!! in the request. This is inherently insecure if not properly restricted.
// !!! Ensure strict path validation and limit readable directories in production.
func UploadFile(c *gin.Context) {
	var request UploadLocalFileRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("无效的请求体: %v", err),
				"type":    "invalid_request_error",
			},
		})
		return
	}

	if request.LocalPath == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": gin.H{
				"message": "请求体缺少 'local_path' 字段",
				"type":    "invalid_request_error",
			},
		})
		return
	}

	// --- 安全检查：限制允许的目录 ---
	// TODO: 考虑从配置或环境变量加载此路径
	allowedBaseDir := `H:\Code\jd_vedio` // 注意 Windows 路径的反斜杠

	// 获取并清理请求的路径
	absRequestPath, err := filepath.Abs(request.LocalPath)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("无效的文件路径: %v", err),
				"type":    "invalid_request_error",
			},
		})
		return
	}
	cleanPath := filepath.Clean(absRequestPath)

	// 清理允许的基目录路径，确保比较时格式一致
	cleanAllowedBaseDir := filepath.Clean(allowedBaseDir)

	// 检查清理后的路径是否在允许的目录下
	// 使用 filepath.Separator 保证跨平台兼容性（虽然当前指定了 Windows 路径）
	// 确保路径后面有分隔符，防止 /allowed/dirabc 被误认为在 /allowed/dir 下
	if !strings.HasPrefix(cleanPath, cleanAllowedBaseDir+string(filepath.Separator)) && cleanPath != cleanAllowedBaseDir {
		c.JSON(http.StatusForbidden, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("禁止访问路径: %s", request.LocalPath), // 不暴露清理后的路径
				"type":    "invalid_request_error",
			},
		})
		return
	}
	// --- 安全检查结束 ---

	// Open the local file (现在路径已经过验证)
	localFile, err := os.Open(cleanPath) // 使用清理后的绝对路径
	if err != nil {
		// Differentiate between file not found and other errors
		errorMsg := fmt.Sprintf("无法打开本地文件 '%s': %v", request.LocalPath, err) // 仍然显示用户原始输入
		errorType := "api_error"
		statusCode := http.StatusInternalServerError
		if os.IsNotExist(err) {
			errorMsg = fmt.Sprintf("本地文件 '%s' 未找到", request.LocalPath)
			statusCode = http.StatusNotFound
			errorType = "invalid_request_error"
		} else if os.IsPermission(err) {
			errorMsg = fmt.Sprintf("无权访问本地文件 '%s'", request.LocalPath)
			statusCode = http.StatusForbidden
			errorType = "invalid_request_error"
		}

		c.JSON(statusCode, gin.H{
			"error": gin.H{
				"message": errorMsg,
				"type":    errorType,
			},
		})
		return
	}
	defer localFile.Close() // Ensure the file is closed

	// Get file info for filename
	fileInfo, err := localFile.Stat()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "无法获取文件信息: " + err.Error()})
		return
	}
	filename := fileInfo.Name()

	// 获取用户信息
	userId := c.GetInt("id")
	user, err := model.GetUserCache(userId)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("获取用户信息失败: %v", err),
				"type":    "api_error",
			},
		})
		return
	}

	// 获取 Gemini 渠道
	channel, err := getGeminiChannel(c, user.Group, "gemini-2.0-flash", 0)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("无法获取有效的 Gemini 渠道: %v", err),
				"type":    "api_error",
			},
		})
		return
	}

	// 从 channel 获取 API Key
	apiKey := channel.Key

	// 使用 relaycommon.GenRelayInfo 获取 RelayInfo 对象
	relayInfo := common.GenRelayInfo(c)

	// 从 RelayInfo 中提取代理 URL
	proxyURL := ""
	if proxySetting, ok := relayInfo.ChannelSetting["proxy"]; ok {
		if proxyStr, isString := proxySetting.(string); isString {
			proxyURL = proxyStr
			log.Printf("使用代理 URL: %s", proxyURL)
		} else {
			log.Printf("Warning: Proxy setting in RelayInfo.ChannelSetting is not a string: %T", proxySetting)
		}
	}

	// 调用 Gemini 文件上传辅助函数
	file, err := gemini.UploadFileReaderToGemini(
		c.Request.Context(),
		apiKey,    // Pass the fetched API Key
		proxyURL,  // Pass the fetched proxy URL (can be empty)
		localFile, // The file reader
		filename,  // The filename
	)

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("上传文件到 Gemini 失败: %v", err),
				"type":    "api_error",
			},
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"uri": file.URI,
		"file": gin.H{
			"name":            file.Name,
			"display_name":    file.DisplayName,
			"mime_type":       file.MIMEType,
			"size_bytes":      file.SizeBytes,
			"create_time":     file.CreateTime,
			"update_time":     file.UpdateTime,
			"expiration_time": file.ExpirationTime,
			"sha256_hash":     file.Sha256Hash,
			"uri":             file.URI,
			"state":           file.State,
		},
		"channel_id": channel.Id, // 添加渠道ID到返回值中
	})
}

// BatchGetFileStatus 处理批量查询文件状态的请求
// 接收一个文件名称列表，返回每个文件的状态信息
func BatchGetFileStatus(c *gin.Context) {
	var request BatchFileStatusRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("无效的请求体: %v", err),
				"type":    "invalid_request_error",
			},
		})
		return
	}

	if len(request.FileNames) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": gin.H{
				"message": "请求体缺少有效的 'file_names' 字段或为空数组",
				"type":    "invalid_request_error",
			},
		})
		return
	}

	// 获取用户信息
	userId := c.GetInt("id")
	user, err := model.GetUserCache(userId)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("获取用户信息失败: %v", err),
				"type":    "api_error",
			},
		})
		return
	}

	// 获取 Gemini 渠道
	channel, err := getGeminiChannel(c, user.Group, "gemini-2.0-flash", 0)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("无法获取有效的 Gemini 渠道: %v", err),
				"type":    "api_error",
			},
		})
		return
	}

	// 从 channel 获取 API Key
	apiKey := channel.Key

	// 使用 relaycommon.GenRelayInfo 获取 RelayInfo 对象
	relayInfo := common.GenRelayInfo(c)

	// 从 RelayInfo 中提取代理 URL
	proxyURL := ""
	if proxySetting, ok := relayInfo.ChannelSetting["proxy"]; ok {
		if proxyStr, isString := proxySetting.(string); isString {
			proxyURL = proxyStr
			log.Printf("批量查询文件状态: 使用代理 URL: %s", proxyURL)
		} else {
			log.Printf("批量查询文件状态: Warning: Proxy setting in RelayInfo.ChannelSetting is not a string: %T", proxySetting)
		}
	}

	// 调用 Gemini 批量查询文件状态函数
	results, err := gemini.BatchGetFileStatus(
		c.Request.Context(),
		apiKey,            // 传递获取的 API Key
		proxyURL,          // 传递获取的代理 URL (可以为空)
		request.FileNames, // 文件名称列表
	)

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("批量查询文件状态失败: %v", err),
				"type":    "api_error",
			},
		})
		return
	}

	// 构造响应
	response := gemini.BatchFileStatusResponse{
		Results: results,
	}

	c.JSON(http.StatusOK, response)
}

// BatchUploadFile 处理批量上传本地文件到 Gemini 的请求
// 所有文件使用相同的渠道进行上传，支持可配置的并发上传
func BatchUploadFile(c *gin.Context) {
	var request BatchUploadFileRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("无效的请求体: %v", err),
				"type":    "invalid_request_error",
			},
		})
		return
	}

	if len(request.LocalPaths) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": gin.H{
				"message": "请求体缺少有效的 'local_paths' 字段或为空数组",
				"type":    "invalid_request_error",
			},
		})
		return
	}

	// 设置固定的模型名称
	modelName := "gemini-2.0-flash"

	// 设置固定的并发数
	concurrency := 5

	// --- 安全检查：限制允许的目录 ---
	// TODO: 考虑从配置或环境变量加载此路径
	allowedBaseDir := `H:\Code\jd_vedio` // 注意 Windows 路径的反斜杠
	cleanAllowedBaseDir := filepath.Clean(allowedBaseDir)

	// 预先验证所有路径
	cleanPaths := make([]string, 0, len(request.LocalPaths))
	for _, path := range request.LocalPaths {
		if path == "" {
			continue // 跳过空路径
		}

		// 获取并清理请求的路径
		absRequestPath, err := filepath.Abs(path)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": gin.H{
					"message": fmt.Sprintf("无效的文件路径 '%s': %v", path, err),
					"type":    "invalid_request_error",
				},
			})
			return
		}
		cleanPath := filepath.Clean(absRequestPath)

		// 检查清理后的路径是否在允许的目录下
		if !strings.HasPrefix(cleanPath, cleanAllowedBaseDir+string(filepath.Separator)) && cleanPath != cleanAllowedBaseDir {
			c.JSON(http.StatusForbidden, gin.H{
				"error": gin.H{
					"message": fmt.Sprintf("禁止访问路径: %s", path), // 不暴露清理后的路径
					"type":    "invalid_request_error",
				},
			})
			return
		}

		cleanPaths = append(cleanPaths, cleanPath)
	}
	// --- 安全检查结束 ---

	// 获取用户信息
	userId := c.GetInt("id")
	user, err := model.GetUserCache(userId)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("获取用户信息失败: %v", err),
				"type":    "api_error",
			},
		})
		return
	}

	// 获取 Gemini 渠道（所有文件共用同一个渠道）
	channel, err := getGeminiChannel(c, user.Group, modelName, 0)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": gin.H{
				"message": fmt.Sprintf("无法获取有效的 Gemini 渠道: %v", err),
				"type":    "api_error",
			},
		})
		return
	}

	// 从 channel 获取 API Key
	apiKey := channel.Key

	// 使用 relaycommon.GenRelayInfo 获取 RelayInfo 对象
	relayInfo := common.GenRelayInfo(c)

	// 从 RelayInfo 中提取代理 URL
	proxyURL := ""
	if proxySetting, ok := relayInfo.ChannelSetting["proxy"]; ok {
		if proxyStr, isString := proxySetting.(string); isString {
			proxyURL = proxyStr
			log.Printf("批量上传文件: 使用代理 URL: %s", proxyURL)
		} else {
			log.Printf("批量上传文件: Warning: Proxy setting in RelayInfo.ChannelSetting is not a string: %T", proxySetting)
		}
	}

	// 创建上传结果结构
	type UploadResult struct {
		OriginalPath string      `json:"original_path"`
		Success      bool        `json:"success"`
		File         *genai.File `json:"file,omitempty"`
		Error        string      `json:"error,omitempty"`
	}

	results := make([]UploadResult, len(cleanPaths))
	resultMap := make(map[string]int) // 映射原始路径到结果数组索引

	// 初始化结果映射
	for i, path := range request.LocalPaths {
		if i < len(cleanPaths) {
			resultMap[path] = i
			results[i] = UploadResult{
				OriginalPath: path,
				Success:      false,
			}
		}
	}

	// 创建并发控制
	var wg sync.WaitGroup
	sem := make(chan struct{}, concurrency)
	var mu sync.Mutex // 保护结果数组的并发访问

	// 并发上传文件
	for i, cleanPath := range cleanPaths {
		originalPath := request.LocalPaths[i]
		wg.Add(1)
		sem <- struct{}{} // 获取信号量

		go func(index int, cPath, origPath string) {
			defer wg.Done()
			defer func() { <-sem }() // 释放信号量

			log.Printf("批量上传: 开始处理文件 %s", origPath)

			// 打开本地文件
			localFile, err := os.Open(cPath)
			if err != nil {
				errorMsg := fmt.Sprintf("无法打开本地文件: %v", err)
				if os.IsNotExist(err) {
					errorMsg = "文件未找到"
				} else if os.IsPermission(err) {
					errorMsg = "无权访问文件"
				}

				mu.Lock()
				results[index] = UploadResult{
					OriginalPath: origPath,
					Success:      false,
					Error:        errorMsg,
				}
				mu.Unlock()
				return
			}
			defer localFile.Close()

			// 获取文件信息
			fileInfo, err := localFile.Stat()
			if err != nil {
				mu.Lock()
				results[index] = UploadResult{
					OriginalPath: origPath,
					Success:      false,
					Error:        fmt.Sprintf("无法获取文件信息: %v", err),
				}
				mu.Unlock()
				return
			}
			filename := fileInfo.Name()

			// 调用 Gemini 文件上传函数
			file, err := gemini.UploadFileReaderToGemini(
				c.Request.Context(),
				apiKey,    // 传递获取的 API Key
				proxyURL,  // 传递获取的代理 URL
				localFile, // 文件读取器
				filename,  // 文件名
			)

			if err != nil {
				mu.Lock()
				results[index] = UploadResult{
					OriginalPath: origPath,
					Success:      false,
					Error:        fmt.Sprintf("上传文件到 Gemini 失败: %v", err),
				}
				mu.Unlock()
				return
			}

			mu.Lock()
			results[index] = UploadResult{
				OriginalPath: origPath,
				Success:      true,
				File:         file,
			}
			mu.Unlock()

			log.Printf("批量上传: 文件 %s 上传成功, URI: %s", origPath, file.URI)
		}(i, cleanPath, originalPath)
	}

	wg.Wait() // 等待所有上传完成

	// 构造最终响应
	c.JSON(http.StatusOK, gin.H{
		"channel_id": channel.Id,
		"results":    results,
	})
}

// getGeminiChannel 复用 relay.go 中的 getChannel 函数逻辑，但使用不同的函数名避免冲突
func getGeminiChannel(c *gin.Context, group, originalModel string, retryCount int) (*model.Channel, error) {
	// 如果指定了特定的渠道 ID，则直接使用该渠道
	if v, exists := c.Get("specific_channel_id"); exists {
		idStr, ok := v.(string)
		if !ok {
			return nil, fmt.Errorf("specific_channel_id 不是字符串类型")
		}
		id, err := strconv.ParseInt(idStr, 10, 64)
		if err != nil {
			return nil, fmt.Errorf("渠道ID格式错误: %w", err)
		}
		c.Set("channel_id", id)
		channel, err := model.GetChannelById(int(id), true)
		if err != nil {
			return nil, fmt.Errorf("无法获取指定渠道: %w", err)
		}
		return channel, nil
	}

	// 否则，获取一个满足条件的随机渠道
	channel, err := model.CacheGetRandomSatisfiedChannel(group, originalModel, retryCount)
	if err != nil {
		return nil, fmt.Errorf("无法获取可用的渠道: %w", err)
	}

	// 记录使用的渠道信息
	useChannel := c.GetStringSlice("use_channel")
	useChannel = append(useChannel, fmt.Sprintf("%d", channel.Id))
	c.Set("use_channel", useChannel)
	c.Set("channel_id", channel.Id)

	return channel, nil
}
