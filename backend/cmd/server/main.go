package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"ai-law-assistant/internal/config"
	"ai-law-assistant/internal/handler"
	"ai-law-assistant/internal/middleware"
	"ai-law-assistant/internal/repository"
	"ai-law-assistant/internal/service"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

func main() {
	// 加载配置
	configPath := os.Getenv("CONFIG_PATH")
	if configPath == "" {
		configPath = "./config/config.yaml"
	}

	cfg, err := config.Load(configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// 初始化数据库
	db, err := initDatabase(cfg)
	if err != nil {
		log.Fatalf("Failed to init database: %v", err)
	}

	// 初始化 Redis
	rdb, err := initRedis(cfg)
	if err != nil {
		log.Fatalf("Failed to init redis: %v", err)
	}

	// 初始化 Repository 层
	userRepo := repository.NewUserRepo(db)
	sessionRepo := repository.NewSessionRepo(db)
	messageRepo := repository.NewMessageRepo(db)
	lawRefRepo := repository.NewLawRefRepo(db)
	auditRepo := repository.NewAuditRepo(db)
	tokenRepo := repository.NewTokenRepo(db)

	// 初始化限流器
	rateLimiter := middleware.NewRateLimiter(rdb)

	// 初始化内容安全过滤器
	contentSafety := middleware.NewContentSafety(cfg.Safety.Enable)

	// 初始化 Service 层
	authService := service.NewAuthService(cfg, userRepo)
	userService := service.NewUserService(userRepo)
	sessionService := service.NewSessionService(sessionRepo, messageRepo)

	searchClient := service.NewSearchClient(service.SearchConfig{
		BaseURL: cfg.Search.BaseURL,
		Timeout: cfg.Search.Timeout,
		TopK:    cfg.Search.TopK,
	})

	llmClient := service.NewLLMClient(service.LLMConfig{
		BaseURL:     cfg.LLM.BaseURL,
		APIKey:      cfg.LLM.APIKey,
		Model:       cfg.LLM.Model,
		Temperature: cfg.LLM.Temperature,
		MaxTokens:   cfg.LLM.MaxTokens,
		Timeout:     cfg.LLM.Timeout,
	})

	contextBuilder := service.NewContextBuilder(3)
	safetyFilter := service.NewSafetyFilter(cfg.Safety.Enable)

	chatService := service.NewChatService(
		messageRepo, sessionRepo, lawRefRepo, auditRepo, tokenRepo,
		searchClient, llmClient, contextBuilder, safetyFilter, contentSafety,
	)

	knowledgeService := service.NewKnowledgeService(searchClient)

	// 初始化 Handler 层
	authHandler := handler.NewAuthHandler(authService, userService)
	userHandler := handler.NewUserHandler(userService)
	sessionHandler := handler.NewSessionHandler(sessionService)
	chatHandler := handler.NewChatHandler(chatService)
	knowledgeHandler := handler.NewKnowledgeHandler(knowledgeService)

	// 初始化 Gin 路由
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()

	// 注册中间件
	router.Use(middleware.Recovery())
	router.Use(middleware.Logger())
	router.Use(middleware.CORS())
	router.Use(contentSafety.Middleware())
	router.Use(rateLimiter.IPRateLimit(cfg.RateLimit.RequestsPerIPPerMinute))

	// API v1 路由组
	v1 := router.Group("/api/v1")
	{
		// 鉴权模块（无需登录）
		auth := v1.Group("/auth")
		{
			auth.POST("/register", authHandler.Register)
			auth.POST("/login", authHandler.Login)
			auth.POST("/refresh", authHandler.RefreshToken)
			auth.POST("/logout", authHandler.Logout)
		}

		// 知识库模块（无需登录）
		knowledge := v1.Group("/knowledge")
		{
			knowledge.GET("/categories", knowledgeHandler.GetCategories)
			knowledge.GET("/search", knowledgeHandler.Search)
			knowledge.GET("/laws/:id", knowledgeHandler.GetLawDetail)
		}

		// 需要登录的接口
		authMW := middleware.Auth(authService.GetJWTManager())
		authed := v1.Group("")
		authed.Use(authMW)
		{
			// 消息限流
			msgRateLimit := rateLimiter.UserMessageRateLimit(cfg.RateLimit.MessagesPerUserPerMinute)

			// 会话模块
			sessions := authed.Group("/sessions")
			{
				sessions.POST("", sessionHandler.Create)
				sessions.GET("", sessionHandler.List)
				sessions.DELETE("/clear-all", sessionHandler.ClearAllHistory) // 清空全部历史（需在 :id 前注册）
				sessions.GET("/:id", sessionHandler.Detail)
				sessions.DELETE("/:id", sessionHandler.Delete)
			}

			// 对话模块
			chat := authed.Group("/chat")
			chat.Use(msgRateLimit)
			{
				chat.POST("/stream", chatHandler.SendMessage)
				chat.GET("/:session_id/messages", chatHandler.GetMessages)
				chat.GET("/:session_id/export", chatHandler.Export)
			}

			// 用户模块
			user := authed.Group("/user")
			{
				user.GET("/profile", userHandler.GetProfile)
				user.PUT("/profile", userHandler.UpdateProfile)
				user.PUT("/privacy", userHandler.UpdatePrivacy)
			}
		}
	}

	// 健康检查
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "time": time.Now().Unix()})
	})

	// 启动 HTTP 服务器
	addr := fmt.Sprintf(":%s", cfg.Server.Port)
	srv := &http.Server{
		Addr:         addr,
		Handler:      router,
		ReadTimeout:  cfg.Server.ReadTimeout,
		WriteTimeout: cfg.Server.WriteTimeout,
	}

	// 优雅退出
	go func() {
		log.Printf("Server starting on %s", addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server exited")
}

func initDatabase(cfg *config.Config) (*gorm.DB, error) {
	db, err := gorm.Open(postgres.Open(cfg.Database.DSN()), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
	})
	if err != nil {
		return nil, fmt.Errorf("connect database: %w", err)
	}

	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("get sql.DB: %w", err)
	}

	sqlDB.SetMaxOpenConns(cfg.Database.MaxOpenConns)
	sqlDB.SetMaxIdleConns(cfg.Database.MaxIdleConns)
	sqlDB.SetConnMaxLifetime(time.Hour)

	// 自动迁移（开发环境）
	// db.AutoMigrate(&model.User{}, &model.Session{}, &model.Message{},
	// 	&model.MessageLawRef{}, &model.AuditLog{}, &model.TokenUsage{}, &model.SMSCode{})

	return db, nil
}

func initRedis(cfg *config.Config) (*redis.Client, error) {
	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.Redis.Addr(),
		Password: cfg.Redis.Password,
		DB:       cfg.Redis.DB,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("connect redis: %w", err)
	}

	return rdb, nil
}
