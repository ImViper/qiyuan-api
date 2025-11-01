package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"one-api/model"

	"gorm.io/gorm"
)

// Gemini API配置
const (
	GeminiBaseURL = "https://generativelanguage.googleapis.com/v1beta"
	DefaultModel  = "gemini-2.5-flash"
	
	// 渠道类型（从系统常量）
	ChannelTypeGemini = 24
	ChannelTypeVertex = 36
)

// TestRequest Gemini测试请求结构
type TestRequest struct {
	Contents []struct {
		Parts []struct {
			Text string `json:"text"`
		} `json:"parts"`
	} `json:"contents"`
	GenerationConfig struct {
		MaxOutputTokens int     `json:"maxOutputTokens"`
		Temperature     float32 `json:"temperature"`
	} `json:"generationConfig"`
}

// TestResult 测试结果
type TestResult struct {
	ChannelID    int           `json:"channel_id"`
	ChannelName  string        `json:"channel_name"`
	Success      bool          `json:"success"`
	Message      string        `json:"message"`
	ResponseTime time.Duration `json:"response_time_ms"`
	Model        string        `json:"model"`
}

// APIKeyTester API密钥测试器
type APIKeyTester struct {
	db      *gorm.DB
	results []TestResult
	mu      sync.Mutex
}

// NewAPIKeyTester 创建新的测试器
func NewAPIKeyTester(dsn string) (*APIKeyTester, error) {
	db, err := model.InitDatabase(dsn)
	if err != nil {
		return nil, err
	}
	return &APIKeyTester{
		db:      db,
		results: make([]TestResult, 0),
	}, nil
}

// TestGeminiKey 测试单个Gemini API密钥
func (t *APIKeyTester) TestGeminiKey(apiKey, modelName, baseURL string) (bool, string, time.Duration) {
	if baseURL == "" {
		baseURL = GeminiBaseURL
	}
	if modelName == "" {
		modelName = DefaultModel
	}

	// 构建URL
	url := fmt.Sprintf("%s/models/%s:generateContent?key=%s", baseURL, modelName, apiKey)

	// 构建测试请求
	req := TestRequest{}
	req.Contents = []struct {
		Parts []struct {
			Text string `json:"text"`
		} `json:"parts"`
	}{
		{
			Parts: []struct {
				Text string `json:"text"`
			}{
				{Text: "Say 'test successful' in 3 words only."},
			},
		},
	}
	req.GenerationConfig.MaxOutputTokens = 10
	req.GenerationConfig.Temperature = 0.1

	jsonData, err := json.Marshal(req)
	if err != nil {
		return false, fmt.Sprintf("Failed to marshal request: %v", err), 0
	}

	// 创建HTTP请求
	httpReq, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return false, fmt.Sprintf("Failed to create request: %v", err), 0
	}
	httpReq.Header.Set("Content-Type", "application/json")

	// 发送请求
	client := &http.Client{
		Timeout: 10 * time.Second,
	}

	start := time.Now()
	resp, err := client.Do(httpReq)
	responseTime := time.Since(start)

	if err != nil {
		return false, fmt.Sprintf("Request failed: %v", err), responseTime
	}
	defer resp.Body.Close()

	// 读取响应
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return false, fmt.Sprintf("Failed to read response: %v", err), responseTime
	}

	// 检查状态码
	switch resp.StatusCode {
	case http.StatusOK:
		// 验证响应格式
		var result map[string]interface{}
		if err := json.Unmarshal(body, &result); err != nil {
			return false, "Invalid JSON response", responseTime
		}
		if candidates, ok := result["candidates"].([]interface{}); ok && len(candidates) > 0 {
			return true, "API key is valid", responseTime
		}
		return false, "Unexpected response format", responseTime

	case http.StatusBadRequest:
		return false, "Invalid API key (400 Bad Request)", responseTime

	case http.StatusForbidden:
		return false, "API key forbidden (403)", responseTime

	case http.StatusNotFound:
		return false, fmt.Sprintf("Model not found: %s", modelName), responseTime

	case http.StatusTooManyRequests:
		return false, "Rate limit exceeded (429)", responseTime

	default:
		return false, fmt.Sprintf("HTTP %d: %s", resp.StatusCode, string(body[:min(100, len(body))]), responseTime
	}
}

// TestChannel 测试单个渠道
func (t *APIKeyTester) TestChannel(channel *model.Channel, testModel string) TestResult {
	result := TestResult{
		ChannelID:   channel.Id,
		ChannelName: channel.Name,
		Model:       testModel,
	}

	// 确定测试模型
	if testModel == "" {
		if channel.TestModel != nil && *channel.TestModel != "" {
			testModel = *channel.TestModel
		} else {
			// 从渠道支持的模型中选择
			models := strings.Split(channel.Models, ",")
			for _, m := range models {
				if strings.Contains(strings.ToLower(m), "gemini") {
					testModel = strings.TrimSpace(m)
					break
				}
			}
			if testModel == "" && len(models) > 0 {
				testModel = strings.TrimSpace(models[0])
			}
			if testModel == "" {
				testModel = DefaultModel
			}
		}
	}
	result.Model = testModel

	// 获取base URL
	baseURL := ""
	if channel.BaseURL != nil {
		baseURL = *channel.BaseURL
	}

	// 处理多个API密钥（换行符分隔）
	keys := strings.Split(strings.TrimSpace(channel.Key), "\n")
	
	for _, key := range keys {
		key = strings.TrimSpace(key)
		if key == "" || strings.HasPrefix(key, "[") || strings.HasPrefix(key, "{") {
			// 跳过空密钥或JSON格式的密钥（Vertex AI）
			continue
		}

		success, message, responseTime := t.TestGeminiKey(key, testModel, baseURL)
		result.Success = success
		result.Message = message
		result.ResponseTime = responseTime / time.Millisecond

		if success {
			return result
		}
	}

	// 如果没有有效的密钥
	if result.Message == "" {
		result.Message = "No valid API key found"
	}

	return result
}

// TestChannels 批量测试渠道
func (t *APIKeyTester) TestChannels(channelType *int, status *int, channelID *int, testModel string, workers int) error {
	// 查询渠道
	query := t.db.Model(&model.Channel{})
	
	if channelID != nil {
		query = query.Where("id = ?", *channelID)
	} else {
		// 默认查询Gemini相关渠道
		if channelType != nil {
			query = query.Where("type = ?", *channelType)
		} else {
			query = query.Where("type IN ?", []int{ChannelTypeGemini, ChannelTypeVertex})
		}
	}
	
	if status != nil {
		query = query.Where("status = ?", *status)
	}

	var channels []model.Channel
	if err := query.Find(&channels).Error; err != nil {
		return fmt.Errorf("failed to query channels: %v", err)
	}

	if len(channels) == 0 {
		fmt.Println("No channels found")
		return nil
	}

	fmt.Printf("Found %d channel(s) to test\n", len(channels))
	fmt.Println(strings.Repeat("=", 60))

	// 使用goroutine池进行并发测试
	var wg sync.WaitGroup
	sem := make(chan struct{}, workers)

	for i, channel := range channels {
		wg.Add(1)
		sem <- struct{}{}
		
		go func(idx int, ch model.Channel) {
			defer wg.Done()
			defer func() { <-sem }()
			
			result := t.TestChannel(&ch, testModel)
			
			t.mu.Lock()
			t.results = append(t.results, result)
			t.mu.Unlock()

			// 打印进度
			statusIcon := "✅"
			if !result.Success {
				statusIcon = "❌"
			}
			fmt.Printf("[%d/%d] %s %s: %s (%dms)\n",
				idx+1, len(channels),
				statusIcon,
				result.ChannelName,
				result.Message,
				result.ResponseTime)
		}(i, channel)
	}

	wg.Wait()
	return nil
}

// PrintSummary 打印测试摘要
func (t *APIKeyTester) PrintSummary() {
	if len(t.results) == 0 {
		return
	}

	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("Test Summary")
	fmt.Println(strings.Repeat("=", 60))

	successful := 0
	var totalResponseTime time.Duration

	for _, r := range t.results {
		if r.Success {
			successful++
			totalResponseTime += r.ResponseTime
		}
	}

	failed := len(t.results) - successful

	fmt.Printf("\nTotal tested: %d\n", len(t.results))
	fmt.Printf("✅ Successful: %d\n", successful)
	fmt.Printf("❌ Failed: %d\n", failed)
	fmt.Printf("Success rate: %.1f%%\n", float64(successful)/float64(len(t.results))*100)

	if successful > 0 {
		avgResponseTime := totalResponseTime / time.Duration(successful)
		fmt.Printf("Average response time: %dms\n", avgResponseTime)
	}

	// 显示失败的渠道
	if failed > 0 {
		fmt.Println("\nFailed channels:")
		for _, r := range t.results {
			if !r.Success {
				fmt.Printf("  - [%d] %s: %s\n", r.ChannelID, r.ChannelName, r.Message)
			}
		}
	}
}

// ExportResults 导出测试结果
func (t *APIKeyTester) ExportResults(filename string) error {
	data := struct {
		TestTime    string       `json:"test_time"`
		Total       int          `json:"total_channels"`
		Successful  int          `json:"successful"`
		Failed      int          `json:"failed"`
		Results     []TestResult `json:"results"`
	}{
		TestTime: time.Now().Format("2006-01-02 15:04:05"),
		Total:    len(t.results),
		Results:  t.results,
	}

	for _, r := range t.results {
		if r.Success {
			data.Successful++
		} else {
			data.Failed++
		}
	}

	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filename, jsonData, 0644)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func main() {
	// 命令行参数
	dsn := flag.String("dsn", "root:123456@tcp(localhost:3306)/new-api", "Database connection string")
	channelType := flag.Int("type", 0, "Channel type (0=all Gemini types)")
	status := flag.Int("status", 0, "Channel status (0=all, 1=enabled, 2=manually disabled, 3=auto disabled)")
	channelID := flag.Int("channel-id", 0, "Test specific channel ID")
	apiKey := flag.String("api-key", "", "Test API key directly")
	model := flag.String("model", "", "Test model (default: gemini-2.5-flash)")
	export := flag.String("export", "", "Export results to JSON file")
	workers := flag.Int("workers", 5, "Number of concurrent workers")
	listModels := flag.Bool("list-models", false, "List supported Gemini models")

	flag.Parse()

	// 列出支持的模型
	if *listModels {
		fmt.Println("Supported Gemini models:")
		models := []string{
			"gemini-2.5-flash",
			"gemini-2.5-pro",
			"gemini-1.5-pro",
			"gemini-1.5-flash",
			"gemini-2.0-flash",
			"gemini-1.5-flash-8b",
			"gemini-1.5-pro-latest",
			"gemini-1.5-flash-latest",
		}
		for _, m := range models {
			fmt.Printf("  - %s\n", m)
		}
		return
	}

	// 直接测试API密钥
	if *apiKey != "" {
		tester := &APIKeyTester{}
		testModel := *model
		if testModel == "" {
			testModel = DefaultModel
		}
		
		fmt.Printf("Testing API key directly with model: %s\n", testModel)
		success, message, responseTime := tester.TestGeminiKey(*apiKey, testModel, "")
		
		if success {
			fmt.Printf("✅ API key is valid! Response time: %dms\n", responseTime/time.Millisecond)
		} else {
			fmt.Printf("❌ API key test failed: %s\n", message)
			os.Exit(1)
		}
		return
	}

	// 创建测试器
	tester, err := NewAPIKeyTester(*dsn)
	if err != nil {
		fmt.Printf("Failed to initialize tester: %v\n", err)
		os.Exit(1)
	}

	// 处理参数
	var channelTypePtr, statusPtr, channelIDPtr *int
	
	if *channelType != 0 {
		channelTypePtr = channelType
	}
	if *status != 0 {
		statusPtr = status
	}
	if *channelID != 0 {
		channelIDPtr = channelID
	}

	// 测试渠道
	if err := tester.TestChannels(channelTypePtr, statusPtr, channelIDPtr, *model, *workers); err != nil {
		fmt.Printf("Error testing channels: %v\n", err)
		os.Exit(1)
	}

	// 打印摘要
	tester.PrintSummary()

	// 导出结果
	if *export != "" {
		if err := tester.ExportResults(*export); err != nil {
			fmt.Printf("Failed to export results: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("\nResults exported to: %s\n", *export)
	}
}