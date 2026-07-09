.PHONY: build run test clean dev

# 编译
build:
	go build -o bin/server ./cmd/server

# 运行
run: build
	./bin/server

# 开发模式（热加载需要安装 air）
dev:
	air

# 测试
test:
	go test ./... -v -cover

# 代码检查
lint:
	golangci-lint run ./...

# 清理
clean:
	rm -rf bin/

# 数据库迁移（手动执行）
migrate:
	psql -h localhost -U ailaw -d ai_law -f migrations/001_schema.sql

# Docker 构建
docker-build:
	docker build -t ai-law-backend:latest .

# Docker 运行
docker-run:
	docker run -p 8080:8080 --env-file .env ai-law-backend:latest
