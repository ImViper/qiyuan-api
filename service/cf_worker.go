package service

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"one-api/common"
	"one-api/setting"
	"strings"
)

// WorkerRequest Worker请求的数据结构
type WorkerRequest struct {
	URL     string            `json:"url"`
	Key     string            `json:"key"`
	Method  string            `json:"method,omitempty"`
	Headers map[string]string `json:"headers,omitempty"`
	Body    json.RawMessage   `json:"body,omitempty"`
}

// DoWorkerRequest 通过Worker发送请求
func DoWorkerRequest(req *WorkerRequest) (*http.Response, error) {
	if !setting.EnableWorker() {
		return nil, fmt.Errorf("worker not enabled")
	}
	if !setting.WorkerAllowHttpImageRequestEnabled && !strings.HasPrefix(req.URL, "https") {
		return nil, fmt.Errorf("only support https url")
	}

	workerUrl := setting.WorkerUrl
	if !strings.HasSuffix(workerUrl, "/") {
		workerUrl += "/"
	}

	// 序列化worker请求数据
	workerPayload, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal worker payload: %v", err)
	}

	return http.Post(workerUrl, "application/json", bytes.NewBuffer(workerPayload))
}

func DoDownloadRequest(originUrl string) (resp *http.Response, err error) {
	// 检查是否是 Gemini API 文件 URL
	if strings.Contains(originUrl, "generativelanguage.googleapis.com/v1beta/files/") {
		common.SysLog(fmt.Sprintf("skipping download for Gemini API file URL: %s", originUrl))
		// 创建一个模拟的响应，包含必要的信息
		// 这样调用方就不会收到错误，但也不会尝试下载文件
		dummyResp := &http.Response{
			StatusCode: http.StatusOK,
			Body:       http.NoBody,
			Header:     make(http.Header),
		}
		// 设置一个通用的 Content-Type
		dummyResp.Header.Set("Content-Type", "application/octet-stream")
		return dummyResp, nil
	}

	if setting.EnableWorker() {
		common.SysLog(fmt.Sprintf("downloading file from worker: %s", originUrl))
		req := &WorkerRequest{
			URL: originUrl,
			Key: setting.WorkerValidKey,
		}
		return DoWorkerRequest(req)
	} else {
		common.SysLog(fmt.Sprintf("downloading from origin: %s", originUrl))
		return http.Get(originUrl)
	}
}
