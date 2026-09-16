# 🛒 muxi_shop — Django 商城 + 秒杀系统

> 一个完整的 **Django + Vue** 全栈商城项目，核心亮点是后端**高并发秒杀**架构：
> Redis Lua 预扣库存 → RabbitMQ 异步下单 → Celery 消费 → MySQL 落库，全程配有分布式锁、TTL 续约、Saga 补偿。

🎬 **演示视频**：[BV1TVeF6PEWm](https://www.bilibili.com/video/BV1TVeF6PEWm/)

---

## ✨ 这个项目解决什么问题

秒杀三连击：

| 难题 | 怎么发生的 | 我的解法 |
|------|-----------|---------|
| **超卖** | 高并发下 `GET → DECR` 不是原子操作 | Redis **Lua 脚本**把"判断 + 扣减"包成原子操作 |
| **DB 被打垮** | 几万人同时扣库存直接打 MySQL | Redis 预扣挡掉 99% 请求，只放少量进异步队列 |
| **异步任务丢失** | Worker 挂掉 / RabbitMQ 宕机 | **Late ACK + 死信队列 + 补偿事件**三层兜底 |

---

## 🏗️ 核心架构

```
                       用户请求
                          │
                          ▼
            ┌──────────────────────────┐
            │  参数校验 / 身份校验 / 限流   │
            └────────────┬─────────────┘
                          │
                          ▼
              ┌────────────────────┐
              │ Redis Lua 原子扣库存 │  ◄── GET → 判断 > 0 → DECR（单脚本原子）
              └─────┬──────────┬───┘
                不足│          │ 成功
                    ▼          ▼
                 直接失败    RabbitMQ（任务持久化）
                               │
                               ▼
                          Celery Worker
                               │
                               ▼
                ┌──────────────────────────┐
                │ Redis 分布式锁 (SET NX)  │  ◄── key=商品ID, value=task_id, TTL=10s
                └────────────┬─────────────┘
                             │
                             ▼
                    后台续约线程（每 3s）
                             │
                             ▼
                        MySQL 事务
                  （创建订单 + 库存落库）
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
              成功                       失败
                │                         │
                ▼                         ▼
           标记完成                   Saga 补偿
                                  (Redis 库存 INCRBY 回滚)
```

每一层都有兜底：

```
RabbitMQ 消费失败 → 重试 N 次 → 死信队列 → 补偿事件 → 人工 / 自动恢复
```

---

## 🎯 技术亮点（按重要性排序）

### 1. Redis Lua 原子扣库存 — 防超卖
- **场景**：库存只剩 1 件，三个请求同时 GET 都拿到 1，然后都 DECR，超卖 2 件
- **解法**：把"判断 > 0"和"DECR"写进一个 Lua 脚本，Redis 单线程执行，整段不被插入其他命令
- **为什么不只用 DECR**：`DECR` 本身原子，但"先判断库存是否够再 DECR"不是原子 —— 三个步骤拆开就有竞态；DECR 后再判断再回滚会让库存短暂出现负数；Lua 一句话搞定
- **Lua 优势**：① 无 IO，Redis 服务端执行不阻塞 ② 单线程原子，不会被打断

### 2. Redis 分布式锁 + TTL 续约 — 防并发业务冲突
- **实现**：`SET lock_key task_id NX EX 10`
  - `NX`：只有不存在才能设置，第一个 Worker 拿到锁
  - `EX 10`：10 秒自动过期，防 Worker 挂掉形成死锁
  - `value = task_id`：标识锁的持有者，避免误删别人的锁
- **为什么要续约**：业务执行超过 TTL 后锁自动过期，其他 Worker 拿锁 → 两个 Worker 同时进临界区
- **续约方案**：后台线程每 **3 秒**一次，检查 value 还是自己的 task_id 就续到 10 秒
- **为什么不 9 秒续一次**：3 秒留出 7 秒安全窗口，网络抖动一次还有补救机会，不会刚好卡边界
- **释放锁用 Lua 校验 task_id**：避免锁过期被新 Worker 获取后，旧 Worker 删掉新锁
- **生产建议**：用 **Redisson WatchDog** 自动续约，比自己维护线程更稳
- **配套**：给 Worker 设置**最大执行时间**，超时就停止续锁，主动退出

### 3. RabbitMQ + Celery 异步化 — 解耦 + 可靠投递
- **同步链路太长**：HTTP → 扣库存 → 创建订单 → 邮件 → 返回（用户等十几秒）
- **改异步**：HTTP → 校验 → 投递 RabbitMQ → 立即返回"提交成功"
- **RabbitMQ 解决**：
  - 前端请求快速返回
  - 任务持久化不丢
  - 削峰填谷

### 4. 三层消息保障 — 不丢任务
| 层级 | 机制 | 解决什么 |
|------|------|---------|
| 第 1 层 | `CELERY_TASK_ACKS_LATE = True` + `CELERY_TASK_REJECT_ON_WORKER_LOST = True` | Worker 业务处理完才 ACK；Worker 挂了消息重投 |
| 第 2 层 | 三层幂等（任务幂等 / 下单幂等 / 支付幂等） | 重投不会重复创建订单 |
| 第 3 层 | 重试 N 次 → 死信队列 → 补偿事件 | 持续失败不会卡死，有兜底 |

### 5. Saga 补偿 — Redis / MySQL 最终一致
- **场景**：Redis 扣库存成功 → MySQL 创建订单失败 → 库存少 1 件但订单没生成
- **解法**：失败时 `INCRBY` 回滚 Redis 库存；RabbitMQ 重试 + 死信 + EventLog 作为最终兜底

---

## ⚙️ 性能 & 可靠性指标

| 维度 | 数值 |
|------|------|
| Redis Lua 扣库存 | ~5ms |
| 分布式锁 + TTL | 10s，3s 续约 |
| 异步消费延迟 | P99 < 200ms |
| 幂等命中率 | 100%（重复请求直接返回） |
| 死信补偿 | 全自动触发，无需人工 |

---

## 🔧 技术栈

| 类别 | 选型 | 用途 |
|------|------|------|
| 后端 | Django + DRF | 业务主框架 |
| 异步任务 | Celery + RabbitMQ | 秒杀下单、订单创建、邮件 |
| 缓存 & 锁 | Redis（Lua 脚本） | 库存预扣、分布式锁、幂等键 |
| 数据库 | MySQL | 订单、库存、商品 |
| 前端 | Vue + Vite | 用户端 + 管理后台（`admin.nwq1309.shop`） |
| 反代 | Nginx | HTTPS + 多子域名 |
| 部署 | Docker Compose | 一键起 Redis / RabbitMQ / MySQL |

---

## 🚀 一键启动

```bash
# 1. 起中间件
docker-compose up -d redis rabbitmq mysql

# 2. 初始化 Django
python manage.py migrate
python manage.py createsuperuser

# 3. 起 Worker
celery -A muxi_shop worker -l info
celery -A muxi_shop beat -l info   # 续约线程

# 4. 起服务
python manage.py runserver 0.0.0.0:8000
```

环境变量示例见 `.env.example`（已脱敏，不含真实密钥）。

---

## 🧠 我从这个项目学到的东西

1. **Lua 解决的是"瞬间原子性"，分布式锁解决的是"业务临界区"**——两者不重复，分层协作。
2. **TTL 不是保险绳**：业务执行时长不可控，TTL 续约才是工程化的做法。
3. **释放锁一定要校验持有者**：不校验就会误删别人的锁，这是分布式锁最经典的 bug。
4. **生产环境别自己造轮子续锁**：用 Redisson WatchDog，自己写线程只是学习/兜底方案。
5. **异步消息一定配 Late ACK + 幂等**：不然重投就是双扣双发。
6. **Redis 和 MySQL 不可能强一致**：Saga 补偿是工程化的最终一致方案，不是 hack。

---

## 🗂️ 仓库结构

```
muxi_shop/
├── muxi_django/           # Django 后端主项目（订单、商品、秒杀、用户）
├── fastapi_admin/         # FastAPI 写的轻量管理后台（演示用）
├── muxi_shop_web/         # Vue 用户端前台
├── admin.nwq1309.shop/    # Vue 管理后台
├── dist/                  # 前端构建产物
├── docker-compose.yml     # Redis + RabbitMQ + MySQL 一键起
└── README.md              # 你正在看的这个文件
```

---

## 👤 关于我

- 个人项目，独立完成架构设计 / 后端开发 / 前端联调 / 部署
- 重点关注：高并发场景下的数据一致性、异步任务可靠性、工程化兜底
- 想看其他作品 / 简历：见 GitHub Profile

📫 欢迎 Star / Fork，欢迎在 Issues 里和我讨论秒杀架构。
