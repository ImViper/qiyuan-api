package gemini

import (
	"context"
	"fmt"
	"google.golang.org/genai"
	"io"
	"log"
	"mime"
	"net/http"
	"net/url"
	"path/filepath"
	"sync"
	"time"
)

const GeminiFileAPIEndpoint = "https://generativelanguage.googleapis.com/v1beta/files"

type GeminiFileResponse struct {
	File struct {
		Name           string    `json:"name"` // e.g., "files/abc-123"
		DisplayName    string    `json:"displayName"`
		MimeType       string    `json:"mimeType"`
		SizeBytes      string    `json:"sizeBytes"` // Note: It's a string in the example
		CreateTime     time.Time `json:"createTime"`
		UpdateTime     time.Time `json:"updateTime"`
		ExpirationTime time.Time `json:"expirationTime"`
		Sha256Hash     string    `json:"sha256Hash"`
		URI            string    `json:"uri"` // This is what we need
	} `json:"file"`
}

type GeminiErrorResponse struct {
	Error struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
		Status  string `json:"status"`
	} `json:"error"`
}

// BatchFileStatusRequest 定义了批量查询文件状态的请求体
type BatchFileStatusRequest struct {
	FileIDs []string `json:"file_ids"` // 文件 ID 列表，例如 ["files/id1", "files/id2"]
}

// FileStatusResult 定义了单个文件的查询结果，包含文件信息或错误
type FileStatusResult struct {
	File  *genai.File `json:"file,omitempty"`  // 成功时返回的文件信息
	Error string      `json:"error,omitempty"` // 失败时返回的错误信息
}

// BatchFileStatusResponse 定义了批量查询文件状态的响应体
type BatchFileStatusResponse struct {
	Results map[string]FileStatusResult `json:"results"` // key 是文件 ID
}

func UploadFileReaderToGemini(ctx context.Context, apiKey string, proxyURL string, fileReader io.Reader, filename string) (*genai.File, error) {
	var httpClient *http.Client

	if proxyURL != "" {
		log.Printf("检测到代理 URL: %s", proxyURL)
		proxyParsedURL, err := url.Parse(proxyURL)
		if err != nil {
			log.Printf("无法解析代理 URL '%s': %v", proxyURL, err)
			return nil, fmt.Errorf("无法解析提供的代理 URL: %w", err)
		}

		transport := &http.Transport{
			Proxy: http.ProxyURL(proxyParsedURL),
		}

		httpClient = &http.Client{
			Transport: transport,
			Timeout:   time.Second * 60,
		}
		log.Printf("已配置使用代理 %s 的 HTTP Client", proxyURL)
	} else {
		log.Printf("未提供代理 URL，将使用默认 HTTP Client")
		httpClient = http.DefaultClient
	}

	clientConfig := &genai.ClientConfig{
		APIKey:     apiKey,
		HTTPClient: httpClient,
	}
	client, err := genai.NewClient(ctx, clientConfig)
	if err != nil {
		log.Printf("无法创建 GenAI 客户端: %v (代理: '%s')", err, proxyURL)
		return nil, fmt.Errorf("无法创建 GenAI 客户端 (代理: '%s'): %w", proxyURL, err)
	}

	mimeType := mime.TypeByExtension(filepath.Ext(filename))
	if mimeType == "" {
		mimeType = "application/octet-stream"
	}

	opts := &genai.UploadFileConfig{
		DisplayName: filename,
		MIMEType:    mimeType,
	}

	log.Printf("使用 SDK 上传文件 (代理: '%s'): DisplayName=%s, MimeType=%s", proxyURL, filename, mimeType)
	file, err := client.Files.Upload(ctx, fileReader, opts)
	if err != nil {
		log.Printf("SDK 上传文件失败 (代理: '%s'): %v", proxyURL, err)
		return nil, fmt.Errorf("SDK 上传文件失败 (代理: '%s'): %w", proxyURL, err)
	}

	if file == nil || file.URI == "" {
		log.Printf("SDK 上传成功 (代理: '%s') 但响应无效: %+v", proxyURL, file)
		return nil, fmt.Errorf("SDK 上传成功 (代理: '%s') 但文件响应无效", proxyURL)
	}

	log.Printf("SDK 上传成功 (代理: '%s'): Name=%s, URI=%s", proxyURL, file.Name, file.URI)
	return file, nil
}

// BatchGetFileStatus 批量查询文件状态
func BatchGetFileStatus(ctx context.Context, apiKey string, proxyURL string, fileNames []string) (map[string]FileStatusResult, error) {
	var httpClient *http.Client

	if proxyURL != "" {
		log.Printf("BatchGetFileStatus: 检测到代理 URL: %s", proxyURL)
		proxyParsedURL, err := url.Parse(proxyURL)
		if err != nil {
			log.Printf("BatchGetFileStatus: 无法解析代理 URL '%s': %v", proxyURL, err)
			return nil, fmt.Errorf("无法解析提供的代理 URL: %w", err)
		}
		transport := &http.Transport{Proxy: http.ProxyURL(proxyParsedURL)}
		httpClient = &http.Client{Transport: transport, Timeout: time.Second * 30} // 查询超时可以短一些
		log.Printf("BatchGetFileStatus: 已配置使用代理 %s 的 HTTP Client", proxyURL)
	} else {
		log.Printf("BatchGetFileStatus: 未提供代理 URL，将使用默认 HTTP Client")
		httpClient = http.DefaultClient
	}

	clientConfig := &genai.ClientConfig{
		APIKey:     apiKey,
		HTTPClient: httpClient,
	}
	client, err := genai.NewClient(ctx, clientConfig)
	if err != nil {
		log.Printf("BatchGetFileStatus: 无法创建 GenAI 客户端: %v (代理: '%s')", err, proxyURL)
		return nil, fmt.Errorf("无法创建 GenAI 客户端 (代理: '%s'): %w", proxyURL, err)
	}

	results := make(map[string]FileStatusResult)
	var wg sync.WaitGroup // 使用 WaitGroup 并发查询
	var mu sync.Mutex     // 保护 results map

	concurrencyLimit := 10
	sem := make(chan struct{}, concurrencyLimit)

	for _, name := range fileNames {
		if name == "" { // 跳过空名称
			continue
		}
		wg.Add(1)
		sem <- struct{}{} // 获取信号量

		go func(fileName string) {
			defer wg.Done()
			defer func() { <-sem }() // 释放信号量

			log.Printf("BatchGetFileStatus: 开始查询文件状态: %s", fileName)
			fileInfo, err := client.Files.Get(ctx, fileName, nil)

			mu.Lock() // 加锁以安全写入 map
			if err != nil {
				log.Printf("BatchGetFileStatus: 查询文件 %s 失败: %v", fileName, err)
				results[fileName] = FileStatusResult{Error: err.Error()}
			} else {
				log.Printf("BatchGetFileStatus: 查询文件 %s 成功: State=%s", fileName, fileInfo.State)
				results[fileName] = FileStatusResult{File: fileInfo}
			}
			mu.Unlock() // 解锁

		}(name) // 将 name 传递给 goroutine
	}

	wg.Wait() // 等待所有查询完成

	return results, nil
}
