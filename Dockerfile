FROM python:3.11-slim

WORKDIR /app

# 替换 Debian 镜像源为科大源，加速 apt-get
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources; \
    else \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list; \
    fi

# 安装 Pillow 图像渲染等所需的系统依赖库
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenjp2-7 \
    libtiff6 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# 使用阿里云源加速 pip 安装（避免清华源 403 限制）
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY . .

# 设置环境变量，确保 Python 能正确寻址模块
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 18080

CMD ["python", "run.py"]
