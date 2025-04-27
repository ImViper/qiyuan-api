package controller

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
	"one-api/model"
	"one-api/relay/channel/gemini"
	"one-api/relay/common"
)

// Request body structure for local file upload
type UploadLocalFileRequest struct {
	LocalPath string `json:"local_path"`
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
	uri, err := gemini.UploadFileReaderToGemini(
		c.Request.Context(),
		apiKey,   // Pass the fetched API Key
		proxyURL, // Pass the fetched proxy URL (can be empty)
		localFile,     // The file reader
		filename, // The filename
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
		"uri": uri,
	})
}

// getGeminiChannel 复用 relay.go 中的 getChannel 函数逻辑，但使用不同的函数名避免冲突
func getGeminiChannel(c *gin.Context, group, originalModel string, retryCount int) (*model.Channel, error) {
	// 如果指定了特定的渠道 ID，则直接使用该渠道
	if specificChannelId, ok := c.Get("specific_channel_id"); ok {
		channelId := specificChannelId.(int)
		c.Set("channel_id", channelId)
		channel, err := model.GetChannelById(channelId, true)
		if err != nil {
			return nil, fmt.Errorf("无法获取指定的渠道: %w", err)
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
