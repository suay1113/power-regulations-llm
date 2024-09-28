#!/bin/bash
mkdir -p logs

# 获取当前日期和时间的字符串，用作日志文件名
current_datetime=$(date +'%Y-%m-%d_%H-%M-%S')

# 构建日志文件的完整路径
llm_log_file="logs/LLM-${current_datetime}.txt"

# 启动显卡与LLM API
CUDA_VISIBLE_DEVICES=4,5,6,7 \
python -m vllm.entrypoints.openai.api_server \
    --host 0.0.0.0 --port 7000 --disable-log-requests --disable-log-stats \
    --model /home/mingjing/weights/qwen/Qwen2___5-14B-Instruct-AWQ --quantization awq \
    --served-model-name Qwen \
    --tensor-parallel-size 4 \
    2>&1 | tee "$llm_log_file"