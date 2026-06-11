FROM python:3.11-slim

WORKDIR /app

# 安装 Pillow 图像渲染等所需的系统依赖库
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenjp2-7 \
    libtiff6 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 设置环境变量，确保 Python 能正确寻址模块
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 18080

CMD ["python", "run.py"]
