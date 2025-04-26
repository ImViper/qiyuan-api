package gemini

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"one-api/common"
	"one-api/dto"
	relaycommon "one-api/relay/common"
	"one-api/service"

	"github.com/gin-gonic/gin"
)

// GeminiImageGenerationResponse 表示Gemini图像生成API的响应格式
type GeminiImageGenerationResponse struct {
	Candidates []struct {
		Content struct {
			Parts []struct {
				Text       string `json:"text,omitempty"`
				InlineData struct {
					MimeType string `json:"mimeType"`
					Data     string `json:"data"`
				} `json:"inlineData,omitempty"`
			} `json:"parts"`
			Role string `json:"role"`
		} `json:"content"`
		FinishReason string `json:"finishReason"`
		Index        int    `json:"index"`
	} `json:"candidates"`
	UsageMetadata struct {
		PromptTokenCount     int `json:"promptTokenCount"`
		CandidatesTokenCount int `json:"candidatesTokenCount"`
		TotalTokenCount      int `json:"totalTokenCount"`
		PromptTokensDetails  []struct {
			Modality   string `json:"modality"`
			TokenCount int    `json:"tokenCount"`
		} `json:"promptTokensDetails"`
		CandidatesTokensDetails []struct {
			Modality   string `json:"modality"`
			TokenCount int    `json:"tokenCount"`
		} `json:"candidatesTokensDetails"`
	} `json:"usageMetadata"`
	ModelVersion string `json:"modelVersion"`
}

// GeminiImageGenerationHandler 处理Gemini图像生成API的响应
func GeminiImageGenerationHandler(c *gin.Context, resp *http.Response, info *relaycommon.RelayInfo) (usage any, err *dto.OpenAIErrorWithStatusCode) {
	responseBody, readErr := io.ReadAll(resp.Body)
	if readErr != nil {
		return nil, service.OpenAIErrorWrapper(readErr, "read_response_body_failed", http.StatusInternalServerError)
	}
	_ = resp.Body.Close()

	var geminiResponse GeminiImageGenerationResponse
	if jsonErr := json.Unmarshal(responseBody, &geminiResponse); jsonErr != nil {
		return nil, service.OpenAIErrorWrapper(jsonErr, "unmarshal_response_body_failed", http.StatusInternalServerError)
	}

	if len(geminiResponse.Candidates) == 0 {
		return nil, service.OpenAIErrorWrapper(errors.New("no images generated"), "no_images", http.StatusBadRequest)
	}

	// 转换为OpenAI格式的响应
	openAIResponse := dto.ImageResponse{
		Created: common.GetTimestamp(),
		Data:    make([]dto.ImageData, 0),
	}

	// 从candidates中提取图像数据
	for _, candidate := range geminiResponse.Candidates {
		for _, part := range candidate.Content.Parts {
			if part.InlineData.MimeType != "" && part.InlineData.Data != "" {
				openAIResponse.Data = append(openAIResponse.Data, dto.ImageData{
					B64Json: part.InlineData.Data,
				})
			}
		}
	}

	// 如果没有找到有效的图像数据
	if len(openAIResponse.Data) == 0 {
		return nil, service.OpenAIErrorWrapper(errors.New("no valid images found in response"), "no_valid_images", http.StatusBadRequest)
	}

	jsonResponse, jsonErr := json.Marshal(openAIResponse)
	if jsonErr != nil {
		return nil, service.OpenAIErrorWrapper(jsonErr, "marshal_response_failed", http.StatusInternalServerError)
	}

	c.Writer.Header().Set("Content-Type", "application/json")
	c.Writer.WriteHeader(resp.StatusCode)
	_, _ = c.Writer.Write(jsonResponse)

	// 计算使用量
	// generatedImages := len(openAIResponse.Data)

	// 使用API返回的实际token计数
	usage = &dto.Usage{
		PromptTokens:     geminiResponse.UsageMetadata.PromptTokenCount,
		CompletionTokens: geminiResponse.UsageMetadata.CandidatesTokenCount,
		TotalTokens:      geminiResponse.UsageMetadata.TotalTokenCount,
	}

	return usage, nil
}
