# Requirements 目录结构

```
requirements/
├── base.txt    # 基础依赖（所有环境共用）
├── local.txt   # 本地开发用（Windows）
└── prod.txt   # 生产服务器用（Linux）
```

## 使用方法

### 本地开发 (Windows)
```bash
uv pip install -r requirements/local.txt
```

### 部署到生产服务器 (Linux)
```bash
uv pip install -r requirements/prod.txt
```

## 说明

- `base.txt`: 包含所有基础 Python 包
- `local.txt`: 引用 base.txt + 本地专用包（不含需要 C++ 编译的包）
- `prod.txt`: 引用 base.txt + 生产专用包（gevent, hiredis, uwsgi, mysqlclient）
