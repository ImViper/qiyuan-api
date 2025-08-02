// Package common 包含渠道管理脚本的共享类型和工具函数
package common

import (
	"fmt"
	"strings"

	"github.com/glebarez/sqlite"
	"gorm.io/driver/mysql"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// Channel 渠道结构体 - 与项目中的结构保持一致
type Channel struct {
	Id                 int     `json:"id"`
	Type               int     `json:"type" gorm:"default:0"`
	Key                string  `json:"key" gorm:"not null"`
	OpenAIOrganization *string `json:"openai_organization"`
	TestModel          *string `json:"test_model"`
	Status             int     `json:"status" gorm:"default:1"`
	Name               string  `json:"name" gorm:"index"`
	Weight             *uint   `json:"weight" gorm:"default:0"`
	CreatedTime        int64   `json:"created_time" gorm:"bigint"`
	TestTime           int64   `json:"test_time" gorm:"bigint"`
	ResponseTime       int     `json:"response_time"` // in milliseconds
	BaseURL            *string `json:"base_url" gorm:"column:base_url;default:''"`
	Other              string  `json:"other"`
	Balance            float64 `json:"balance"` // in USD
	BalanceUpdatedTime int64   `json:"balance_updated_time" gorm:"bigint"`
	Models             string  `json:"models"`
	Group              string  `json:"group" gorm:"type:varchar(64);default:'default'"`
	UsedQuota          int64   `json:"used_quota" gorm:"bigint;default:0"`
	ModelMapping       *string `json:"model_mapping" gorm:"type:text"`
	StatusCodeMapping  *string `json:"status_code_mapping" gorm:"type:varchar(1024);default:''"`
	Priority           *int64  `json:"priority" gorm:"bigint;default:0"`
	AutoBan            *int    `json:"auto_ban" gorm:"default:1"`
	OtherInfo          string  `json:"other_info"`
	Tag                *string `json:"tag" gorm:"index"`
	Setting            *string `json:"setting" gorm:"type:text"` // 渠道额外设置
	ParamOverride      *string `json:"param_override" gorm:"type:text"`
	ChannelInfo        *string `json:"channel_info" gorm:"type:json"` // 简化为字符串类型
}

// 轻量级Channel结构体 - 用于快速导出
type LightChannel struct {
	Id          int     `json:"id"`
	Type        int     `json:"type"`
	Key         string  `json:"key"`
	Name        string  `json:"name"`
	Status      int     `json:"status"`
	Balance     float64 `json:"balance"`
	Models      string  `json:"models"`
	Group       string  `json:"group"`
	CreatedTime int64   `json:"created_time"`
}

// ConnectDB 连接数据库 - 共享函数
func ConnectDB(dsn string) (*gorm.DB, error) {
	var dialector gorm.Dialector
	
	if strings.HasPrefix(dsn, "sqlite:") {
		dbPath := strings.TrimPrefix(dsn, "sqlite:")
		dialector = sqlite.Open(dbPath)
	} else if strings.Contains(dsn, "tcp(") {
		dialector = mysql.Open(dsn)
	} else if strings.Contains(dsn, "host=") {
		dialector = postgres.Open(dsn)
	} else {
		return nil, fmt.Errorf("不支持的数据库类型: %s", dsn)
	}

	db, err := gorm.Open(dialector, &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("打开数据库失败: %v", err)
	}

	return db, nil
}

// MaskString 隐藏敏感字符串
func MaskString(s string) string {
	if len(s) <= 8 {
		return "***masked***"
	}
	return s[:4] + "***masked***" + s[len(s)-4:]
}

// MaskDSN 隐藏数据库连接字符串中的密码
func MaskDSN(dsn string) string {
	if strings.Contains(dsn, "password=") || strings.Contains(dsn, ":") {
		return "***masked***"
	}
	return dsn
}