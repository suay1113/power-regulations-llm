import os
import json
import logging
import pandas as pd

from datetime import datetime
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import List, Dict, Union, Optional

from utils.call_ocr import ocr
from utils.call_api import model_answer
from utils.parse import remove_word, extract_numbers, parse_json, safe_eval
from utils.file_process import random_name, save_base64_images


# ======= 初始化 =======
DEFAULT_API_PATH = "./cache/api/"
IMAGE_FOLDER = os.path.join(DEFAULT_API_PATH, "images")
LOGS_PATH = "./cache/logs"
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(LOGS_PATH, exist_ok=True)
app = FastAPI()

# 设置日志
logging.basicConfig(filename=os.path.join(LOGS_PATH, f'API_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ======= 请求体结构 =======
class OCRData(BaseModel):
    paths: List[str]
    # images: List[str] = None # List of base64-encoded images
    # pdf: str = None # Optional path to PDF file

class logicData(BaseModel):
    ticket_data: Dict # 字典
    random: bool = False # 是否随机
    raw_ocr: str = None  # 原始ocr

class workerData(BaseModel):
    ticket_data: Dict # 字典
    random: bool = False # 是否随机
    raw_ocr: str = None  # 原始ocr


# ======= 基础函数 =======
def parse_ocr_text(image_files):
    ocr_results = {'positions': [], 'ocr_data': []}

    for index, image_file in enumerate(image_files):
        success, ocr_output = ocr(image_file)
        ocr_results['positions'].append(index)
        ocr_results['ocr_data'].append(ocr_output if success else "")

    df_results = pd.DataFrame(ocr_results).sort_values(by='positions').reset_index(drop=True)
    ticket_text = "".join(df_results['ocr_data'].values)
    
    parsed_text = []
    current_line = ""
    for char in ticket_text:
        if char[0].isdigit() and (len(char) > 2 and char[1] == '.'):
            if current_line:
                parsed_text.append(current_line.strip())
            current_line = char
        else:
            current_line += " " + char
    
    if current_line:
        parsed_text.append(current_line.strip())
    
    final_sentence = ''.join(parsed_text)
    
    # Remove incomplete parentheses
    if final_sentence.startswith('(') and final_sentence.endswith(')'):
        final_sentence = final_sentence[1:-1]
    elif final_sentence.startswith('('):
        final_sentence = final_sentence[1:]
    
    return final_sentence


# ======= FastAPI =======
# @app.post("/ocr-info")
# async def ocr_info(input: OCRData):   #(file: UploadFile = File(...)):
#     try:
#         if input.images is not None:
#             folder_name = random_name()
#             folder_path = os.path.join(IMAGE_FOLDER, folder_name)
#             image_paths = save_base64_images(input.images, folder_path)
#             msg = f"[ocr-info] 接收到图片：{image_paths}"
#             logger.info(msg)
#         elif input.pdf is not None:
#             msg = f"[ocr-info] pdf输入开发中: {input}"
#             logger.error(msg)
#             return {'status': 41, 'message': msg}
#         else:
#             msg = f"[ocr-info] Invalid OCRData: {input}"
#             logger.error(msg)
#             return {'status': 41, 'message': msg}
#     except Exception as e:
#         msg = f"[ocr-info] 预处理错误: {e}"
#         logger.error(msg)
#         return {'status': 41, 'message': msg}

@app.post("/ocr-info")
async def ocr_info(
    files: Optional[List[UploadFile]] = File(None),
    paths: Optional[str] = Form(None)
):
    try:
        folder_name = random_name()
        folder_path = os.path.join(IMAGE_FOLDER, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        files_list = []
        if paths:
            paths = json.loads(paths)
            for file in paths:
                if os.path.exists(file):
                    files_list.append(file)
                else:
                    msg = f"[ocr-info] 此文件失效，无法找到路径：{file}"
                    logger.error(msg)
        elif files:
            for file in files:
                if isinstance(file, UploadFile):    # 如果是 UploadFile 类型，保存文件
                    logger.info(f"{file.filename}")
                    file_location = os.path.join(folder_path, file.filename)
                    with open(file_location, "wb") as buffer:
                        buffer.write(await file.read())
                    files_list.append(file_location)
        else:
            msg = "[ocr-info] No files or paths received"
            logger.error(msg)
            return {'status': 41, 'message': msg}
        msg = f"[ocr-info] 接收到文件：{files_list}"
        logger.info(msg)
    except Exception as e:
        msg = f"[ocr-info] 预处理错误: {e}"
        logger.error(msg)
        return {'status': 41, 'message': msg}

    try:
        # Perform OCR
        ocr_result = parse_ocr_text(files_list)
        prompt_text = f"工作票内容为：{ocr_result}"
        format_template = "提炼工作票中信息，填充入下面的字典中,不能改变格式，格式为：\
            {'工作负责人':, '工作班成员(不包括工作负责人)':[],'工作的线路名称或设备双重名称(多回路应注明双重称号)':,'工作任务':\
            ,'工作许可时间':\
            ,'计划工作开始时间':\
            ,'工作终结时间':\
            ,'工作签发时间':\
            ,'工作负责人':\
            ,'工作负责人人员签名':\
            ,'工作票延期':\
            ,'现场所挂的接地线编号':\
            ,'确认工作负责人布置的工作任务和安全措施工作班组人员签名':[]\
            ,'工作终结报告':\
            ,'备注':\
            ,'工作票延期时间':\
            ,'工作负责人变动情况':}。\
            不要进行额外联想和补充,如果没有则写无。只输出字典，不输出其他信息"

        # Get processed response from model
        processed_response = model_answer(prompt_text, format_template)

    except Exception as e:
        msg = f"[ocr-info] 推理错误: {e}"
        logger.error(msg)
        return {'status': 42, 'message': msg}

    try:
        try:
            ticket_data = safe_eval(processed_response)
            date_fields = ["工作许可时间", "计划工作开始时间", "工作签发时间", "工作终结时间", "工作票延期时间"]
            for field in date_fields:
                if field in ticket_data:
                    if ticket_data[field] != '无':
                        ticket_data[field] = datetime.strptime(ticket_data[field], "%Y年%m月%d日%H时%M分")
                else:
                    logger.warning(f"[ocr-info] 未在OCR结果中找到{field}")

        except ValueError as ve:
            msg = f"[ocr-info] 工作票后处理错误: {ve}"
            logger.error(msg)
            return {'status': 43, 'message': msg}
        except Exception as e:
            msg = f"[ocr-info] 工作票错误: {e}"
            logger.error(msg)
            return {'status': 43, 'message': msg}

        return {'status': 20, 'message': "[ocr-info] 完成", "ticket_data": ticket_data, "raw_ocr_result": ocr_result}

    except Exception as e:
        msg = f"[ocr-info] 未知错误: {e}"
        logger.error(msg)
        return {'status': 40, 'message': msg}


@app.post("/logic-check")
async def get_logic_error(input: logicData):
    try:
        ticket_data = input.ticket_data
        random_flag = input.random if input.random else False
        raw_ocr = input.raw_ocr  if input.raw_ocr else None
    except Exception as e:
        msg = f"[logic-check] 预处理错误: {e}"
        logger.error(msg)
        return {'status': 41, 'message': msg}

    prompt = f"""工作票整体要求：每张工作票最多允许3处错、漏字，每处不超过3个字（不含标点符号）。\n
具体要求:
1. 工作任务："工作内容"栏中，每段或每基杆塔的工作内容应填写具体且明确，且内容要与实际工作对应。  
2. 许可工作:
   - "确认本工作票1-6项，许可工作开始"（或"许可工作内容"）部分，要求工作负责人签名与“工作负责人（监护人）”中的签名一致。若不一致，应与"工作负责人变动情况"中最新的负责人一致。  
   - 许可时间应在计划工作开始时间之后或与之相同。特殊情况许可时间可早于计划时间，但需在"备注"内注明原因。  
   - 许可方式为当面通知、电话下达、或派人送达。电话下达和派人送达时，工作负责人代写工作许可人姓名；若工作许可人在场，须由本人亲自签名。
3. 工作班组签名:
   - "确认工作负责人布置的工作任务和安全措施"部分，需工作班组人员签名，且签名人员与“工作班成员（不含工作负责人）”一致。若不一致，需检查“工作人员变动情况”，核对实际人员。  
   - 签名须由本人亲自签署，不允许盖章或代签。多页工作票仅需在首页签名。若使用工作任务单，工作组负责人在工作票上签名确认，组员在各自任务单上签名。\n\n
已知安全规范要求:
- 工作负责人在发出开始工作的命令前，必须得到所有工作许可人的许可，并在工作票上签名确认。  
- 开工前，工作负责人或签发人应重新核对现场勘察情况，发现变化时需调整安全措施。  
- 实际工作线路名称、杆号应与工作票内容一致，工作负责人需到达现场核对情况。  
- 若涉及停电的交叉跨越或邻近线路，需在线路附近装设接地线，同杆塔架设线路与检修线路的接地线要求相同。\n
----
现在工人实际填写的工作票内容为：\n{ticket_data}
"""
    sys_prompt = """你现在是一个工具，负责判断工人填写的工作票是否符合规定的「要求」，并返回json格式：  
- 若工作票内容全部符合要求
- 若发现不符合要求的内容，请简明扼要地指出
**注意事项**：  
- 错误描述需基于工作票的实际情况。  
- 仅罗列不符合要求的部分，无需列出符合要求的内容。"""

    try:
        if random_flag:
            error_response = model_answer(prompt, sys_prompt, tmp=0.2)
        else:
            error_response = model_answer(prompt, sys_prompt, tmp=0.01)
        return {"status":20, "message":"完成", "logic_errors": error_response}
    
    except Exception as e:
        msg = f"[logic-check] 预处理错误: {e}"
        logger.error(msg)
        return {'status': 41, 'message': msg}

@app.post("/worker-check")
async def get_worker_error(input: workerData):
    try:
        ticket_data = input.ticket_data
        random_flag = input.random if input.random else False
        raw_ocr = input.raw_ocr  if input.raw_ocr else None
    except Exception as e:
        msg = f"[worker-check] 预处理错误: {e}"
        logger.error(msg)
        return {'status': 41, 'message': msg}
    
    worker_error_message = {}
    try:
        ticket_data = safe_eval(ticket_data)
        worker_error_message["人数"] = f"工作班成员不包含工作负责人个数为{len(ticket_data['工作班成员(不包括工作负责人)'])}，请检查人数是否一致"
        if ticket_data['工作负责人'] in (ticket_data['工作班成员(不包括工作负责人)']):
            worker_error_message["工作班成员"] = "工作班成员包含工作负责人，不符合安规要求"
        if ticket_data['工作负责人'] != ticket_data['工作负责人人员签名']:
            worker_error_message['工作负责人签名'] = "工作负责人人员签名与工作班负责人不一致，但也有可能由于字迹潦草导致无法识别导致，请进行检查"
        if ticket_data['工作班成员(不包括工作负责人)'] != ticket_data['确认工作负责人布置的工作任务和安全措施工作班组人员签名']:
            worker_error_message["工作班成员签名"] = "工作班人员签名与工作班人数不一致，但也有可能由于字迹潦草导致无法识别导致，请进行检查"
        return {'status': 20, 'message': "完成", "worker_errors": worker_error_message}
        
    except ValueError as e:
        msg = f"[worker-check] 格式不符合，无法判断时间是否正确: {e}"
        logger.error(msg)
        return {'status': 42, 'message': msg}
    except Exception as e:
        msg = f"[worker-check] 未知错误: {e}"
        logger.error(msg)
        return {'status': 40, 'message': msg}
