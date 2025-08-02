package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/joho/godotenv"
	"gorm.io/gorm"
	"qiyuan-api-scripts/common"
)

// 使用共享的Channel类型
type Channel = common.Channel

// ChannelBackupData 备份数据结构
type ChannelBackupData struct {
	ExportTime    string    `json:"export_time"`
	ExportVersion string    `json:"export_version"`
	TotalChannels int       `json:"total_channels"`
	DatabaseInfo  string    `json:"database_info"`
	Channels      []Channel `json:"channels"`
}

// ImportResult 导入结果
type ImportResult struct {
	Total   int      `json:"total"`
	Success int      `json:"success"`
	Failed  int      `json:"failed"`
	Skipped int      `json:"skipped"`
	Errors  []string `json:"errors"`
}

// 渠道类型映射
var ChannelTypeNames = map[int]string{
	1: "OpenAI", 2: "API2D", 3: "Azure", 4: "CloseAI", 5: "CloseAI-SB",
	6: "OpenSB", 7: "AI-LS", 8: "AI-LS2", 9: "AI-LS3", 10: "AI360",
	11: "PaLM", 12: "Baidu", 13: "Zhipu", 14: "Ali", 15: "Xunfei",
	16: "AI-Proxy", 17: "OpenRouter", 18: "AI-LB", 19: "Replicate", 20: "Midjourney",
	21: "Anthropic", 22: "AWS", 23: "Cohere", 24: "Custom", 25: "Gemini",
	26: "Moonshot", 27: "Baichuan", 28: "Minimax", 29: "DeepSeek", 30: "Groq",
	31: "Ollama", 32: "PerplexityAI", 33: "Cloudflare", 34: "Lingyiwanwu", 35: "Doubao",
	36: "Tencent", 37: "Dify", 38: "Vertex", 39: "Coze", 40: "Jina",
	41: "Mistral", 42: "Siliconflow", 43: "Xinference", 44: "MidjourneyPlus", 45: "Suno",
	46: "Jimeng", 47: "Mokaai", 48: "Kling", 49: "XAI",
}

// 渠道状态映射
var ChannelStatusNames = map[int]string{
	0: "Unknown", 1: "Enabled", 2: "Manually Disabled", 3: "Auto Disabled",
}

func main() {
	var (
		action         = flag.String("action", "export", "操作类型: export, import, backup, restore")
		sqlDSN         = flag.String("dsn", "", "数据库连接字符串 (如果为空则尝试从环境变量获取)")
		inputFile      = flag.String("input", "", "导入文件路径 (用于import/restore操作)")
		outputFile     = flag.String("output", "", "输出文件路径 (默认: channels_backup_TIMESTAMP.json)")
		format         = flag.String("format", "json", "输出格式: json, csv, txt (仅用于export)")
		help           = flag.Bool("help", false, "显示帮助信息")
		verbose        = flag.Bool("verbose", false, "显示详细信息")
		maskKeys       = flag.Bool("mask-keys", true, "是否隐藏敏感的API密钥信息 (仅用于export)")
		filterType     = flag.Int("type", -1, "按渠道类型过滤 (-1表示全部)")
		filterStatus   = flag.Int("status", -1, "按状态过滤 (-1表示全部)")
		skipExisting   = flag.Bool("skip-existing", true, "导入时跳过已存在的渠道")
		updateExisting = flag.Bool("update-existing", false, "导入时更新已存在的渠道")
		dryRun         = flag.Bool("dry-run", false, "模拟运行，不实际操作数据库")
	)

	flag.Parse()

	if *help {
		printHelpV1()
		return
	}

	// 加载 .env 文件
	if err := godotenv.Load(); err != nil && *verbose {
		log.Printf("未找到 .env 文件: %v", err)
	}

	// 获取数据库连接字符串
	dbDSN := *sqlDSN
	if dbDSN == "" {
		dbDSN = os.Getenv("SQL_DSN")
	}
	if dbDSN == "" {
		// Docker Compose MySQL 默认配置
		dbDSN = "root:123456@tcp(localhost:3306)/new-api"
	}

	if *verbose {
		log.Printf("使用数据库连接: %s", maskDSN(dbDSN))
		log.Printf("操作类型: %s", *action)
	}

	// 连接数据库
	db, err := common.ConnectDB(dbDSN)
	if err != nil {
		log.Fatalf("连接数据库失败: %v", err)
	}

	switch *action {
	case "export":
		err = handleExport(db, *outputFile, *format, *maskKeys, *filterType, *filterStatus, *verbose)
	case "import":
		err = handleImport(db, *inputFile, *skipExisting, *updateExisting, *dryRun, *verbose)
	case "backup":
		err = handleBackup(db, *outputFile, *verbose)
	case "restore":
		err = handleRestore(db, *inputFile, *dryRun, *verbose)
	default:
		log.Fatalf("未知操作类型: %s (支持: export, import, backup, restore)", *action)
	}

	if err != nil {
		log.Fatalf("操作失败: %v", err)
	}
}

func printHelpV1() {
	fmt.Println(`
渠道管理工具 - 支持导入导出功能
用法: go run channel_manager.go -action=<操作> [选项]

操作类型:
  export   导出渠道数据（可选择格式）
  import   导入渠道数据（从JSON文件）
  backup   备份所有渠道数据（包含完整信息）
  restore  恢复渠道数据（从备份文件）

通用选项:
  -dsn string         数据库连接字符串 (默认从环境变量SQL_DSN获取)
  -verbose            显示详细信息
  -help               显示此帮助信息

导出选项:
  -output string      输出文件路径 (默认: channels_export_TIMESTAMP.json)
  -format string      输出格式: json, csv, txt (默认: json)
  -mask-keys          是否隐藏敏感的API密钥信息 (默认: true)
  -type int           按渠道类型过滤 (-1表示全部, 默认: -1)
  -status int         按状态过滤 (-1表示全部, 默认: -1)

导入选项:
  -input string       输入文件路径 (必需)
  -skip-existing      跳过已存在的渠道 (默认: true)
  -update-existing    更新已存在的渠道 (默认: false)
  -dry-run            模拟运行，不实际操作数据库

备份/恢复选项:
  -output string      备份文件路径 (backup操作)
  -input string       恢复文件路径 (restore操作)
  -dry-run            模拟运行，不实际操作数据库

Docker Compose 数据库连接:
  默认连接字符串: root:123456@tcp(localhost:3306)/new-api
  如果使用 Docker Compose，请确保 MySQL 端口已映射到主机

示例用法:
  # 导出所有渠道
  go run channel_manager.go -action=export

  # 导出为CSV格式
  go run channel_manager.go -action=export -format=csv

  # 备份所有渠道数据
  go run channel_manager.go -action=backup

  # 从备份文件恢复
  go run channel_manager.go -action=restore -input=backup.json

  # 导入渠道数据（跳过重复）
  go run channel_manager.go -action=import -input=channels.json

  # 导入并更新已存在的渠道
  go run channel_manager.go -action=import -input=channels.json -update-existing

  # 模拟导入（不实际操作）
  go run channel_manager.go -action=import -input=channels.json -dry-run`)
}

// connectDB 已移至 common 包

func handleExport(db *gorm.DB, outputFile, format string, maskKeys bool, filterType, filterStatus int, verbose bool) error {
	channels, err := getAllChannels(db, filterType, filterStatus)
	if err != nil {
		return fmt.Errorf("获取渠道数据失败: %v", err)
	}

	if verbose {
		log.Printf("找到 %d 个渠道", len(channels))
	}

	if maskKeys {
		maskSensitiveData(channels)
	}

	outputPath := outputFile
	if outputPath == "" {
		timestamp := time.Now().Format("20060102_150405")
		switch format {
		case "csv":
			outputPath = fmt.Sprintf("channels_export_%s.csv", timestamp)
		case "txt":
			outputPath = fmt.Sprintf("channels_export_%s.txt", timestamp)
		default:
			outputPath = fmt.Sprintf("channels_export_%s.json", timestamp)
		}
	}

	if err := os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
		return fmt.Errorf("创建输出目录失败: %v", err)
	}

	switch format {
	case "csv":
		err = exportToCSV(channels, outputPath)
	case "txt":
		err = exportToTXT(channels, outputPath)
	default:
		err = exportToJSON(channels, outputPath)
	}

	if err != nil {
		return fmt.Errorf("导出数据失败: %v", err)
	}

	fmt.Printf("✅ 成功导出 %d 个渠道到文件: %s\n", len(channels), outputPath)
	return nil
}

func handleBackup(db *gorm.DB, outputFile string, verbose bool) error {
	channels, err := getAllChannels(db, -1, -1)
	if err != nil {
		return fmt.Errorf("获取渠道数据失败: %v", err)
	}

	if verbose {
		log.Printf("备份 %d 个渠道", len(channels))
	}

	outputPath := outputFile
	if outputPath == "" {
		timestamp := time.Now().Format("20060102_150405")
		outputPath = fmt.Sprintf("channels_backup_%s.json", timestamp)
	}

	backupData := ChannelBackupData{
		ExportTime:    time.Now().Format("2006-01-02 15:04:05"),
		ExportVersion: "1.0.0",
		TotalChannels: len(channels),
		DatabaseInfo:  "MySQL Docker Compose",
		Channels:      channels,
	}

	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("创建备份文件失败: %v", err)
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(backupData); err != nil {
		return fmt.Errorf("写入备份数据失败: %v", err)
	}

	fmt.Printf("✅ 成功备份 %d 个渠道到文件: %s\n", len(channels), outputPath)
	return nil
}

func handleImport(db *gorm.DB, inputFile string, skipExisting, updateExisting, dryRun, verbose bool) error {
	if inputFile == "" {
		return fmt.Errorf("导入操作必须指定输入文件 (-input)")
	}

	data, err := loadImportData(inputFile)
	if err != nil {
		return fmt.Errorf("加载导入文件失败: %v", err)
	}

	if verbose {
		log.Printf("准备导入 %d 个渠道", len(data.Channels))
	}

	result := &ImportResult{}
	result.Total = len(data.Channels)

	for _, channel := range data.Channels {
		if err := processChannelImport(db, channel, skipExisting, updateExisting, dryRun, verbose, result); err != nil {
			result.Errors = append(result.Errors, fmt.Sprintf("渠道 %s (ID:%d): %v", channel.Name, channel.Id, err))
			result.Failed++
		} else {
			result.Success++
		}
	}

	printImportResult(result, dryRun)
	return nil
}

func handleRestore(db *gorm.DB, inputFile string, dryRun, verbose bool) error {
	if inputFile == "" {
		return fmt.Errorf("恢复操作必须指定输入文件 (-input)")
	}

	data, err := loadImportData(inputFile)
	if err != nil {
		return fmt.Errorf("加载恢复文件失败: %v", err)
	}

	if verbose {
		log.Printf("准备恢复 %d 个渠道", len(data.Channels))
		log.Printf("备份信息: %s, 版本: %s", data.ExportTime, data.ExportVersion)
	}

	if !dryRun {
		// 在恢复前先备份当前数据
		backupFile := fmt.Sprintf("pre_restore_backup_%s.json", time.Now().Format("20060102_150405"))
		if err := handleBackup(db, backupFile, false); err != nil {
			log.Printf("⚠️ 创建恢复前备份失败: %v", err)
		} else {
			log.Printf("✅ 已创建恢复前备份: %s", backupFile)
		}

		// 删除现有渠道数据
		if err := db.Exec("DELETE FROM channels").Error; err != nil {
			return fmt.Errorf("清空现有渠道数据失败: %v", err)
		}
		if verbose {
			log.Printf("已清空现有渠道数据")
		}
	}

	result := &ImportResult{}
	result.Total = len(data.Channels)

	for _, channel := range data.Channels {
		if !dryRun {
			if err := db.Create(&channel).Error; err != nil {
				result.Errors = append(result.Errors, fmt.Sprintf("恢复渠道 %s (ID:%d): %v", channel.Name, channel.Id, err))
				result.Failed++
			} else {
				result.Success++
			}
		} else {
			result.Success++
		}
	}

	printRestoreResult(result, dryRun)
	return nil
}

func loadImportData(inputFile string) (*ChannelBackupData, error) {
	file, err := os.Open(inputFile)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var data ChannelBackupData
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&data); err != nil {
		return nil, err
	}

	return &data, nil
}

func processChannelImport(db *gorm.DB, channel Channel, skipExisting, updateExisting, dryRun, verbose bool, result *ImportResult) error {
	// 检查渠道是否已存在
	var existingChannel Channel
	err := db.Where("name = ? OR (id = ? AND id > 0)", channel.Name, channel.Id).First(&existingChannel).Error

	exists := err == nil

	if exists && skipExisting && !updateExisting {
		if verbose {
			log.Printf("跳过已存在的渠道: %s (ID:%d)", channel.Name, channel.Id)
		}
		result.Skipped++
		return nil
	}

	if !dryRun {
		if exists && updateExisting {
			// 更新现有渠道
			channel.Id = existingChannel.Id // 保持原有ID
			if err := db.Save(&channel).Error; err != nil {
				return err
			}
			if verbose {
				log.Printf("更新渠道: %s (ID:%d)", channel.Name, channel.Id)
			}
		} else if !exists {
			// 创建新渠道
			channel.Id = 0 // 让数据库自动分配ID
			if err := db.Create(&channel).Error; err != nil {
				return err
			}
			if verbose {
				log.Printf("创建新渠道: %s (ID:%d)", channel.Name, channel.Id)
			}
		}
	} else {
		if exists && updateExisting {
			if verbose {
				log.Printf("[模拟] 更新渠道: %s", channel.Name)
			}
		} else if !exists {
			if verbose {
				log.Printf("[模拟] 创建新渠道: %s", channel.Name)
			}
		}
	}

	return nil
}

func printImportResult(result *ImportResult, dryRun bool) {
	action := "导入"
	if dryRun {
		action = "模拟导入"
	}

	fmt.Printf("\n📊 %s结果统计:\n", action)
	fmt.Printf("总计: %d\n", result.Total)
	fmt.Printf("成功: %d\n", result.Success)
	fmt.Printf("失败: %d\n", result.Failed)
	fmt.Printf("跳过: %d\n", result.Skipped)

	if len(result.Errors) > 0 {
		fmt.Printf("\n❌ 错误详情:\n")
		for _, err := range result.Errors {
			fmt.Printf("  - %s\n", err)
		}
	}

	if dryRun {
		fmt.Printf("\n💡 这是模拟运行，没有实际修改数据库\n")
	}
}

func printRestoreResult(result *ImportResult, dryRun bool) {
	action := "恢复"
	if dryRun {
		action = "模拟恢复"
	}

	fmt.Printf("\n📊 %s结果统计:\n", action)
	fmt.Printf("总计: %d\n", result.Total)
	fmt.Printf("成功: %d\n", result.Success)
	fmt.Printf("失败: %d\n", result.Failed)

	if len(result.Errors) > 0 {
		fmt.Printf("\n❌ 错误详情:\n")
		for _, err := range result.Errors {
			fmt.Printf("  - %s\n", err)
		}
	}

	if dryRun {
		fmt.Printf("\n💡 这是模拟运行，没有实际修改数据库\n")
	} else {
		fmt.Printf("\n✅ 数据库已恢复到备份状态\n")
	}
}

// 以下函数复用之前的代码
func getAllChannels(db *gorm.DB, filterType, filterStatus int) ([]Channel, error) {
	var channels []Channel

	query := db

	if filterType >= 0 {
		query = query.Where("type = ?", filterType)
	}

	if filterStatus >= 0 {
		query = query.Where("status = ?", filterStatus)
	}

	if err := query.Find(&channels).Error; err != nil {
		return nil, err
	}

	return channels, nil
}

func maskSensitiveData(channels []Channel) {
	for i := range channels {
		if channels[i].Key != "" {
			channels[i].Key = common.MaskString(channels[i].Key)
		}
		if channels[i].Other != "" {
			channels[i].Other = common.MaskString(channels[i].Other)
		}
	}
}

func maskDSN(dsn string) string {
	return common.MaskDSN(dsn)
}

func exportToJSON(channels []Channel, outputPath string) error {
	exportData := ChannelBackupData{
		ExportTime:    time.Now().Format("2006-01-02 15:04:05"),
		ExportVersion: "1.0.0",
		TotalChannels: len(channels),
		DatabaseInfo:  "Export",
		Channels:      channels,
	}

	file, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(exportData)
}

func exportToCSV(channels []Channel, outputPath string) error {
	file, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer file.Close()

	headers := []string{
		"ID", "Name", "Type", "TypeName", "Status", "StatusName", "Group", "Weight",
		"Priority", "Balance", "UsedQuota", "Models", "BaseURL", "CreatedTime", "TestTime",
		"ResponseTime", "Tag", "Key", "Other", "Setting",
	}

	file.WriteString(strings.Join(headers, ",") + "\n")

	for _, channel := range channels {
		row := []string{
			strconv.Itoa(channel.Id),
			fmt.Sprintf(`"%s"`, channel.Name),
			strconv.Itoa(channel.Type),
			fmt.Sprintf(`"%s"`, getChannelTypeName(channel.Type)),
			strconv.Itoa(channel.Status),
			fmt.Sprintf(`"%s"`, getChannelStatusName(channel.Status)),
			fmt.Sprintf(`"%s"`, channel.Group),
			formatUintPtr(channel.Weight),
			formatInt64Ptr(channel.Priority),
			fmt.Sprintf("%.2f", channel.Balance),
			strconv.FormatInt(channel.UsedQuota, 10),
			fmt.Sprintf(`"%s"`, channel.Models),
			formatStringPtr(channel.BaseURL),
			formatTimestamp(channel.CreatedTime),
			formatTimestamp(channel.TestTime),
			strconv.Itoa(channel.ResponseTime),
			formatStringPtr(channel.Tag),
			fmt.Sprintf(`"%s"`, channel.Key),
			fmt.Sprintf(`"%s"`, channel.Other),
			formatStringPtr(channel.Setting),
		}

		file.WriteString(strings.Join(row, ",") + "\n")
	}

	return nil
}

func exportToTXT(channels []Channel, outputPath string) error {
	file, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer file.Close()

	file.WriteString(fmt.Sprintf("渠道导出报告 - %s\n", time.Now().Format("2006-01-02 15:04:05")))
	file.WriteString(fmt.Sprintf("总计: %d 个渠道\n\n", len(channels)))
	file.WriteString(strings.Repeat("=", 80) + "\n\n")

	for _, channel := range channels {
		file.WriteString(fmt.Sprintf("渠道ID: %d\n", channel.Id))
		file.WriteString(fmt.Sprintf("名称: %s\n", channel.Name))
		file.WriteString(fmt.Sprintf("类型: %s (%d)\n", getChannelTypeName(channel.Type), channel.Type))
		file.WriteString(fmt.Sprintf("状态: %s (%d)\n", getChannelStatusName(channel.Status), channel.Status))
		file.WriteString(fmt.Sprintf("分组: %s\n", channel.Group))

		if channel.Weight != nil {
			file.WriteString(fmt.Sprintf("权重: %d\n", *channel.Weight))
		}
		if channel.Priority != nil {
			file.WriteString(fmt.Sprintf("优先级: %d\n", *channel.Priority))
		}

		file.WriteString(fmt.Sprintf("余额: %.2f USD\n", channel.Balance))
		file.WriteString(fmt.Sprintf("已用额度: %d\n", channel.UsedQuota))
		file.WriteString(fmt.Sprintf("支持模型: %s\n", channel.Models))

		if channel.BaseURL != nil && *channel.BaseURL != "" {
			file.WriteString(fmt.Sprintf("基础URL: %s\n", *channel.BaseURL))
		}

		if channel.Tag != nil && *channel.Tag != "" {
			file.WriteString(fmt.Sprintf("标签: %s\n", *channel.Tag))
		}

		file.WriteString(fmt.Sprintf("创建时间: %s\n", formatTimestamp(channel.CreatedTime)))
		file.WriteString(fmt.Sprintf("最后测试: %s\n", formatTimestamp(channel.TestTime)))

		if channel.ResponseTime > 0 {
			file.WriteString(fmt.Sprintf("响应时间: %d ms\n", channel.ResponseTime))
		}

		file.WriteString(fmt.Sprintf("API密钥: %s\n", channel.Key))

		if channel.Setting != nil && *channel.Setting != "" {
			file.WriteString(fmt.Sprintf("设置: %s\n", *channel.Setting))
		}

		file.WriteString("\n" + strings.Repeat("-", 80) + "\n\n")
	}

	return nil
}

func getChannelTypeName(typeId int) string {
	if name, exists := ChannelTypeNames[typeId]; exists {
		return name
	}
	return fmt.Sprintf("Unknown (%d)", typeId)
}

func getChannelStatusName(status int) string {
	if name, exists := ChannelStatusNames[status]; exists {
		return name
	}
	return fmt.Sprintf("Unknown (%d)", status)
}

func formatStringPtr(s *string) string {
	if s == nil {
		return `""`
	}
	return fmt.Sprintf(`"%s"`, *s)
}

func formatUintPtr(u *uint) string {
	if u == nil {
		return "0"
	}
	return strconv.FormatUint(uint64(*u), 10)
}

func formatInt64Ptr(i *int64) string {
	if i == nil {
		return "0"
	}
	return strconv.FormatInt(*i, 10)
}

func formatTimestamp(ts int64) string {
	if ts == 0 {
		return `""`
	}
	return fmt.Sprintf(`"%s"`, time.Unix(ts, 0).Format("2006-01-02 15:04:05"))
}
