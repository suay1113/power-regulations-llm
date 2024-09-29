# 安规LLM
## 算法结构
* 本项目为前后端分离技术，在任何CPU下均可运行
* OCR服务作为后端
* vllm作为大模型后端，OpenAI格式
* api.py 核心部分为API，包括以下接口：
    - **ocr-info**: files: Optional[List[UploadFile]] = File(None),paths: Optional[str] = Form(None)
    - **logic-check**: ticket_data: Dict, random: bool = False, raw_ocr: str = None 
    - **worker-check**: ticket_data: Dict, random: bool = False, raw_ocr: str = None 
* demo-main.py

## 配置方案
### 240930
- 目前至少需要3个conda环境，且相互隔离，分别为
    1. OCR环境，基于paddleOCR，未在本项目中实现
    2. vllm环境，基于vllm、pytorch等，直接`pip install vllm`即可
    3. QAnything环境，后期将考虑与vllm环境合并
- 安装本项目依赖：`pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/`
- 下一步将合并环境，避免过多服务

## 启动命令
0. 启动OCR服务，目前用的paddle，在另一个服务;
1. 启动LLM`sh script/start_llm14B_api.sh`; 
2. 启动API`sh script/start.sh`;
3. 启动demo`python demo-main.py`

## 底层技术
1. OCR解析图片或pdf
2. LLM为 Qwen-17B
3. 预期使用QAnything技术