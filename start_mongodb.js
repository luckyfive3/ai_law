/**
 * 使用 mongodb-memory-server 启动本地 MongoDB 实例
 * 数据持久化到 mongodb_data 目录
 */
const { MongoMemoryServer } = require('mongodb-memory-server');

async function startMongo() {
  const mongod = await MongoMemoryServer.create({
    instance: {
      port: 27017,
      dbPath: 'c:/Users/luck/Desktop/ai_law/ai_law/mongodb_data',
      storageEngine: 'wiredTiger',
    },
    binary: {
      version: '7.0.14',
    },
    // 启动后不自动停止
  });

  const uri = mongod.getUri();
  console.log(`MongoDB 已启动: ${uri}`);
  console.log('按 Ctrl+C 停止...');

  // 保持进程运行
  process.on('SIGINT', async () => {
    console.log('\n正在停止 MongoDB...');
    await mongod.stop();
    console.log('MongoDB 已停止');
    process.exit(0);
  });
}

startMongo().catch(err => {
  console.error('MongoDB 启动失败:', err);
  process.exit(1);
});
