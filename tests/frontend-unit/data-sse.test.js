/**
 * laws_data.js 和 SSE 解析逻辑单元测试
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

// Load laws_data.js
const lawsPath = resolve(__dirname, '../../frontend/static/js/laws_data.js');
const lawsContent = readFileSync(lawsPath, 'utf-8');
// Extract just enough to validate — the file sets window.LAWS_DATA
const indirectEval = eval;
indirectEval(lawsContent);

describe('LAWS_DATA 法律数据库', () => {
  const data = globalThis.window.LAWS_DATA;

  it('数据非空数组', () => {
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeGreaterThan(0);
  });

  it('每条记录包含必要字段', () => {
    for (const law of data.slice(0, 10)) {
      expect(law).toHaveProperty('id');
      expect(law).toHaveProperty('name');
      expect(law).toHaveProperty('category');
      expect(law).toHaveProperty('articles');
      expect(Array.isArray(law.articles)).toBe(true);
    }
  });

  it('id 唯一', () => {
    const ids = data.map(l => l.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('articles 包含必要字段', () => {
    const first = data[0];
    expect(first.articles.length).toBeGreaterThan(0);
    const article = first.articles[0];
    expect(article).toHaveProperty('content');
    expect(typeof article.content).toBe('string');
    expect(article.content.length).toBeGreaterThan(0);
  });

  it('category 是有效类别', () => {
    const validCats = ['marriage', 'labor', 'contract', 'traffic',
      'housing', 'consumer', 'criminal', 'general'];
    for (const law of data.slice(0, 5)) {
      expect(validCats).toContain(law.category);
    }
  });
});

describe('SSE 数据行解析器', () => {
  /**
   * 模拟 chat.js 中的 SSE 解析逻辑
   * 这是核心流式消息解析算法
   */
  function parseSSEBuffer(buffer, lines) {
    const results = [];
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const jsonStr = line.substring(5).trim();
      if (!jsonStr) continue;
      try {
        results.push(JSON.parse(jsonStr));
      } catch (e) {
        // skip malformed JSON
      }
    }
    return results;
  }

  it('解析 searching 状态', () => {
    const events = parseSSEBuffer('', [
      'data: {"status":"searching","index":0}',
    ]);
    expect(events).toHaveLength(1);
    expect(events[0].status).toBe('searching');
  });

  it('解析 generating 状态含 content', () => {
    const events = parseSSEBuffer('', [
      'data: {"status":"generating","content":"你好","index":0}',
    ]);
    expect(events).toHaveLength(1);
    expect(events[0].content).toBe('你好');
  });

  it('解析 done 事件含 tokens', () => {
    const events = parseSSEBuffer('', [
      'data: {"done":true,"status":"done","message_id":"msg1","tokens":{"input":10,"output":20}}',
    ]);
    expect(events).toHaveLength(1);
    expect(events[0].done).toBe(true);
    expect(events[0].tokens.input).toBe(10);
  });

  it('解析 error 状态', () => {
    const events = parseSSEBuffer('', [
      'data: {"status":"error","error":"内容包含敏感信息"}',
    ]);
    expect(events).toHaveLength(1);
    expect(events[0].status).toBe('error');
  });

  it('忽略非 data: 开头的行', () => {
    const events = parseSSEBuffer('', [
      'event: ping',
      'data: {"status":"generating","content":"ok","index":0}',
      '',
    ]);
    expect(events).toHaveLength(1);
    expect(events[0].status).toBe('generating');
  });

  it('忽略空 data 行', () => {
    const events = parseSSEBuffer('', [
      'data: ',
      'data: {"status":"done","done":true,"message_id":"m1","tokens":{}}',
    ]);
    expect(events).toHaveLength(1);
  });

  it('容忍格式错误的 JSON', () => {
    const events = parseSSEBuffer('', [
      'data: {invalid json}',
      'data: {"status":"generating","content":"ok","index":0}',
    ]);
    expect(events).toHaveLength(1);
    expect(events[0].status).toBe('generating');
  });

  it('流式多 token 顺序解析', () => {
    const events = parseSSEBuffer('', [
      'data: {"status":"searching","index":0}',
      'data: {"status":"generating","content":"根","index":0}',
      'data: {"status":"generating","content":"据","index":1}',
      'data: {"status":"generating","content":"民","index":2}',
      'data: {"status":"generating","content":"法","index":3}',
      'data: {"status":"generating","content":"典","index":4}',
      'data: {"done":true,"status":"done","message_id":"m1","tokens":{"input":5,"output":5}}',
    ]);
    expect(events).toHaveLength(7);
    const content = events.filter(e => e.content).map(e => e.content).join('');
    expect(content).toBe('根据民法典');
  });
});
