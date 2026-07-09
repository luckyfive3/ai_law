package config

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	Server    ServerConfig    `mapstructure:"server"`
	Database  DatabaseConfig  `mapstructure:"database"`
	Redis     RedisConfig     `mapstructure:"redis"`
	JWT       JWTConfig       `mapstructure:"jwt"`
	LLM       LLMConfig       `mapstructure:"llm"`
	Search    SearchConfig    `mapstructure:"search"`
	Safety    SafetyConfig    `mapstructure:"safety"`
	RateLimit RateLimitConfig `mapstructure:"rate_limit"`
}

type ServerConfig struct {
	Port         string        `mapstructure:"port"`
	ReadTimeout  time.Duration `mapstructure:"read_timeout"`
	WriteTimeout time.Duration `mapstructure:"write_timeout"`
}

type DatabaseConfig struct {
	Host         string `mapstructure:"host"`
	Port         int    `mapstructure:"port"`
	Name         string `mapstructure:"name"`
	User         string `mapstructure:"user"`
	Password     string `mapstructure:"password"`
	MaxOpenConns int    `mapstructure:"max_open_conns"`
	MaxIdleConns int    `mapstructure:"max_idle_conns"`
}

func (d DatabaseConfig) DSN() string {
	return fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable TimeZone=Asia/Shanghai",
		d.Host, d.Port, d.User, d.Password, d.Name)
}

type RedisConfig struct {
	Host     string `mapstructure:"host"`
	Port     int    `mapstructure:"port"`
	Password string `mapstructure:"password"`
	DB       int    `mapstructure:"db"`
}

func (r RedisConfig) Addr() string {
	return fmt.Sprintf("%s:%d", r.Host, r.Port)
}

type JWTConfig struct {
	Secret      string        `mapstructure:"secret"`
	AccessTTL   time.Duration `mapstructure:"access_ttl"`
	RefreshTTL  time.Duration `mapstructure:"refresh_ttl"`
}

type LLMConfig struct {
	Provider    string        `mapstructure:"provider"`
	BaseURL     string        `mapstructure:"base_url"`
	APIKey      string        `mapstructure:"api_key"`
	Model       string        `mapstructure:"model"`
	Temperature float64       `mapstructure:"temperature"`
	MaxTokens   int           `mapstructure:"max_tokens"`
	Timeout     time.Duration `mapstructure:"timeout"`
	MaxRetries  int           `mapstructure:"max_retries"`
}

type SearchConfig struct {
	BaseURL string        `mapstructure:"base_url"`
	Timeout time.Duration `mapstructure:"timeout"`
	TopK    int           `mapstructure:"top_k"`
}

type SafetyConfig struct {
	Enable       bool   `mapstructure:"enable"`
	KeywordsFile string `mapstructure:"keywords_file"`
}

type RateLimitConfig struct {
	MessagesPerUserPerMinute int `mapstructure:"messages_per_user_per_minute"`
	RequestsPerIPPerMinute   int `mapstructure:"requests_per_ip_per_minute"`
	Burst                    int `mapstructure:"burst"`
}

func Load(configPath string) (*Config, error) {
	v := viper.New()

	if configPath != "" {
		v.SetConfigFile(configPath)
	} else {
		v.SetConfigName("config")
		v.SetConfigType("yaml")
		v.AddConfigPath("./config")
		v.AddConfigPath(".")
	}

	// 自动替换环境变量
	v.AutomaticEnv()
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	// 从环境变量覆盖敏感配置
	cfg.Database.Host = envOr("DB_HOST", cfg.Database.Host)
	cfg.Database.User = envOr("DB_USER", cfg.Database.User)
	cfg.Database.Password = envOr("DB_PASSWORD", cfg.Database.Password)
	cfg.Redis.Host = envOr("REDIS_HOST", cfg.Redis.Host)
	cfg.Redis.Password = envOr("REDIS_PASSWORD", cfg.Redis.Password)
	cfg.JWT.Secret = envOr("JWT_SECRET", cfg.JWT.Secret)
	cfg.LLM.APIKey = envOr("DEEPSEEK_API_KEY", cfg.LLM.APIKey)

	return &cfg, nil
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
