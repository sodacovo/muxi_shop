# 1. 基础镜像：匹配你的Python 3.12版本
FROM python:3.12-slim

# 2. 安装系统依赖（解决Django依赖编译问题，如mysqlclient）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*  # 清理缓存，减小镜像体积

# 3. 设置工作目录（容器内的项目根路径）
WORKDIR /app

# 4. 复制依赖文件并安装（用清华源加速，避免超时）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 复制整个项目文件到容器（.dockerignore会自动排除无用文件）
COPY . .

# 6. 暴露端口（和你uwsgi.ini配置的端口一致，默认8000）
EXPOSE 8000

# 7. 启动命令（用uwsgi启动，和你本地生产环境一致）
CMD ["uwsgi", "--ini", "uwsgi.ini"]
