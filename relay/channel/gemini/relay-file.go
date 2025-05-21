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

func UploadFileReaderToGemini(ctx context.Context, apiKey string, proxyURL string, fileReader io.Reader, filename string) (string, error) {
	var httpClient *http.Client

	if proxyURL != "" {
		log.Printf("检测到代理 URL: %s", proxyURL)
		proxyParsedURL, err := url.Parse(proxyURL)
		if err != nil {
			log.Printf("无法解析代理 URL '%s': %v", proxyURL, err)
			return "", fmt.Errorf("无法解析提供的代理 URL: %w", err)
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
	}

	clientConfig := &genai.ClientConfig{
		APIKey:     apiKey,
		HTTPClient: httpClient,
	}
	client, err := genai.NewClient(ctx, clientConfig)
	if err != nil {
		log.Printf("无法创建 GenAI 客户端: %v (代理: '%s')", err, proxyURL)
		return "", fmt.Errorf("无法创建 GenAI 客户端 (代理: '%s'): %w", proxyURL, err)
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
		return "", fmt.Errorf("SDK 上传文件失败 (代理: '%s'): %w", proxyURL, err)
	}

	if file == nil || file.URI == "" {
		log.Printf("SDK 上传成功 (代理: '%s') 但响应无效: %+v", proxyURL, file)
		return "", fmt.Errorf("SDK 上传成功 (代理: '%s') 但文件响应无效", proxyURL)
	}

	log.Printf("SDK 上传成功 (代理: '%s'): Name=%s, URI=%s", proxyURL, file.Name, file.URI)
	return file.URI, nil
}
