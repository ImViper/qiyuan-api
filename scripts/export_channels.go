// 轻量级渠道导出工具
// 使用channel_manager.go的完整功能，这个脚本专门用于快速导出
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"github.com/joho/godotenv"
	"gorm.io/gorm"
	"qiyuan-api-scripts/common"
)

// 简化的导出数据结构
type ExportData struct {
	ExportTime    string                `json:"export_time"`
	TotalChannels int                   `json:"total_channels"`
	Channels      []common.LightChannel `json:"channels"`
}

func main() {
	var (
		sqlDSN     = flag.String("dsn", "", "数据库连接字符串")
		outputFile = flag.String("output", "", "输出文件路径")
		help       = flag.Bool("help", false, "显示帮助信息")
		maskKeys   = flag.Bool("mask-keys", true, "隐藏API密钥")
	)
	
	flag.Parse()

	if *help {
		printHelp()
		return
	}

	// 简化的环境配置
	godotenv.Load()
	dbDSN := *sqlDSN
	if dbDSN == "" {
		dbDSN = os.Getenv("SQL_DSN")
		if dbDSN == "" {
			dbDSN = "root:123456@tcp(localhost:3306)/new-api" // Docker默认
		}
	}

	// 连接数据库并导出
	db, err := common.ConnectDB(dbDSN)
	if err != nil {
		log.Fatalf("数据库连接失败: %v", err)
	}

	channels, err := getChannels(db)
	if err != nil {
		log.Fatalf("获取数据失败: %v", err)
	}

	if *maskKeys {
		maskChannelKeys(channels)
	}

	outputPath := *outputFile
	if outputPath == "" {
		outputPath = fmt.Sprintf("channels_quick_export_%s.json", time.Now().Format("20060102_150405"))
	}

	if err := exportJSON(channels, outputPath); err != nil {
		log.Fatalf("导出失败: %v", err)
	}

	fmt.Printf("✅ 导出完成: %s (%d个渠道)\n", outputPath, len(channels))
}

func printHelp() {
	fmt.Print(`
轻量级渠道导出工具
用法: go run export_channels.go [选项]

选项:
  -dsn string     数据库连接字符串 (默认使用Docker配置)
  -output string  输出文件路径 (默认: channels_quick_export_时间.json)
  -mask-keys      隐藏API密钥 (默认: true)
  -help           显示帮助

注意: 如需完整功能，请使用 channel_manager.go
`)
}

// 获取所有渠道（简化版） - 只查询必需字段
func getChannels(db *gorm.DB) ([]common.LightChannel, error) {
	var channels []common.LightChannel
	return channels, db.Table("channels").Select("id, type, `key`, name, status, balance, models, `group`, created_time").Find(&channels).Error
}

// 简化的密钥隐藏
func maskChannelKeys(channels []common.LightChannel) {
	for i := range channels {
		if len(channels[i].Key) > 8 {
			channels[i].Key = channels[i].Key[:4] + "***" + channels[i].Key[len(channels[i].Key)-4:]
		} else {
			channels[i].Key = "***"
		}
	}
}

// 简化的JSON导出
func exportJSON(channels []common.LightChannel, outputPath string) error {
	data := ExportData{
		ExportTime:    time.Now().Format("2006-01-02 15:04:05"),
		TotalChannels: len(channels),
		Channels:      channels,
	}

	os.MkdirAll(filepath.Dir(outputPath), 0755)
	file, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(data)
}

