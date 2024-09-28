import os, re
import glob
import nest_asyncio
nest_asyncio.apply()

import numpy as np
import pandas as pd
from tqdm import tqdm
from datetime import datetime

from utils.call_ocr import ocr
from utils.call_api import model_answer
from utils.parse import remove_word, extract_numbers, safe_eval

async def search_db(paper1, db):
    searched_docs = await db.asimilarity_search(paper1,50)
    return searched_docs
    
async def mmr_search_db(paper1, db):
    searched_docs = await db.amax_marginal_relevance_search(paper1, k=1000, fetch_k=10)
    return searched_docs

def extract_ocr_from_images(base_path):
    image_files = sorted(glob.glob(os.path.join(base_path, '*')))
    print(f"[OCR文件]读取并分析以下文件：{image_files}")
    results = {'pos': [], 'ocr': []}

    for position_index, image_file in enumerate(image_files):
        flag, ocr_result = ocr(image_file)   
        if flag:
            results['pos'].append(position_index)
            results['ocr'].append(ocr_result)
        else:
            results['pos'].append(position_index)
            results['ocr'].append("")

    return results

def get_ocr_info(img_path):
    all_result = extract_ocr_from_images(img_path)
    
    res = pd.DataFrame(all_result).sort_values(by='pos').reset_index(drop=True)
    print(res.head())
    ticket = ""
    for i in range(res.shape[0]):
        ticket += res.loc[i,'ocr']
    data = ticket 
    new_data = []
    current_number = None
    current_line = ""
    for item in data:
        if item[0].isdigit() and (len(item) > 2 and item[1] == '.'):
            if current_line:
                new_data.append(current_line.strip())
            current_line = item
            current_number = item[:2]
        else:
            if current_number is not None:
                current_line += " " + item
            else:
                new_data.append(item)
    
    if current_line:
        new_data.append(current_line.strip())
    sentence = ''.join(new_data)

    # 去除括号（如果括号不完整可以根据实际情况调整）
    if sentence.startswith('(') and sentence.endswith(')'):
        sentence = sentence[1:-1]
    elif sentence.startswith('('):
        sentence = sentence[1:]
    return sentence


def get_core_info(img_path, heads):
    result = get_ocr_info(os.path.join(img_path, heads))

    prompt=f"现在工作票内容为：{result}"
    answer_find = "提炼工作票中信息，填充入下面的字典中,不能改变格式，格式为：{'工作负责人':, '工作班成员(不包括工作负责人)':[],'工作的线路名称或设备双重名称(多回路应注明双重称号)':,'工作任务':\
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
    ,'工作负责人变动情况':}。不要进行额外联想和补充,如果没有则写无。只输出字典，不输出其他信息"
    are = model_answer(prompt, answer_find, tmp=0.001)
    try:
        are = safe_eval(are)
        if are["工作许可时间"] != '无':
            are["工作许可时间"] = datetime.strptime(are["工作许可时间"], "%Y年%m月%d日%H时%M分")
        if are["计划工作开始时间"] != '无':
            are["计划工作开始时间"] = datetime.strptime(are["计划工作开始时间"], "%Y年%m月%d日%H时%M分")
        if are["工作签发时间"] != '无':
            are["工作签发时间"] = datetime.strptime(are["工作签发时间"], "%Y年%m月%d日%H时%M分")
        if are["工作终结时间"] != '无':
            are["工作终结时间"] = datetime.strptime(are["工作终结时间"], "%Y年%m月%d日%H时%M分")
        if are['工作票延期时间'] != '无':
            are['工作票延期时间'] = datetime.strptime(are['工作票延期时间'], "%Y年%m月%d日%H时%M分")            
                
    except ValueError:
        print(f"格式不符合，保持原形式存储")
    return are, result

def time_error(are):
    error = ""
    try:
        are = safe_eval(are)
        if (are["计划工作开始时间"] != '无') & (are["工作许可时间"] != '无'):
            if (are["工作许可时间"] >= are["计划工作开始时间"]):
                error += '工作许可时间不能在计划开始时间之后'
                print('工作许可时间不能在计划开始时间之后')
        elif (are["计划工作开始时间"] == '无') :
            print("计划工作开始时间为空")
            error += "\n"+'计划工作开始时间为空'
        elif (are["工作许可时间"] == '无'):
            print("工作许可时间为空")
            error += "\n"+'工作许可时间为空'
        
        if (are["工作终结时间"] != '无') & (are["计划工作开始时间"] != '无'):
            if (are["工作终结时间"] < are["计划工作开始时间"]):
                error += '\n' + '工作终结时间不能在计划工作开始时间之前'
                print('工作终结时间不能在计划工作开始时间之前')
        elif (are["工作终结时间"] == '无'):
            print("工作终结时间为空")
            error += '\n' + "工作终结时间为空"

        if (are["工作终结时间"] != '无') & (are["工作许可时间"] != '无'):
            if (are["工作终结时间"] < are["工作许可时间"]):
                error += '\n' + '工作终结时间不能在工作许可时间之前'
                print('工作终结时间不能在工作许可时间之前')
                
        
        if (are["工作签发时间"] != '无') & (are["计划工作开始时间"] != '无'):   
            if (are["工作签发时间"] >= are["计划工作开始时间"]):
                error += '\n' + '工作签发时间不能在计划工作开始时间之后'
                print('工作签发时间不能在计划工作开始时间之后')
        elif (are["工作签发时间"] == '无'):
            print("工作签发时间为空")
            error += "工作签发时间为空"

        if (are["工作终结时间"] != '无') & (are["工作签发时间"] != '无'):
            if (are["工作终结时间"] < are["工作签发时间"]):
                error += '\n' + '工作终结时间不能在工作签发时间之前'
                print('工作终结时间不能在工作签发时间之前')

        
        if len(error) == 0: 
            error = "时间无误"
    except ValueError:
        print(f"日期格式不符合，无法判断时间是否正确")
    return error
    
def get_worker_error(are):
    error = ""
    try:
        are = safe_eval(are)
        error += f"工作班成员不包含工作负责人个数为{len(are['工作班成员(不包括工作负责人)'])}，请检查人数是否一致"
        # print(f"工作班成员不包含工作负责人个数为{len(are['工作班成员(不包括工作负责人)'])}，请检查人数是否一致")
        if are['工作负责人'] in (are['工作班成员(不包括工作负责人)']):
            error += '\n' + "工作班成员包含工作负责人，不符合安规要求"
            # print("工作班成员包含工作负责人，不符合安规要求")
        if are['工作负责人'] != are['工作负责人人员签名']:
            error += "\n" + "工作负责人人员签名与工作班负责人不一致，但也有可能由于字迹潦草导致无法识别导致，请进行检查"
            # print("工作负责人人员签名与工作班负责人不一致，但也有可能由于字迹潦草导致无法识别导致，请进行检查")
        if are['工作班成员(不包括工作负责人)'] != are['确认工作负责人布置的工作任务和安全措施工作班组人员签名']:
            error += "\n" + "工作班人员签名与工作班人数不一致，但也有可能由于字迹潦草导致无法识别导致，请进行检查"
    except ValueError:
        print(f"格式不符合，无法判断时间是否正确")
    return error 

def get_luoji_error(are, result):    
    luoji_prompt = "工厂中需要将工人的操作行为进行记录，并称为工作票，\
                    你现在是一个工具，判断工人实际填写的工作票内容是否符合「要求」。工作票内容和对应的要求如下，不要自行增加其他要求：\
                    工作票全篇要求：一份工作票不允许超过3处错、漏字，每处不超过3个字，不计算标点符号导致的错误。\
                    （3）「工作任务」，工作内容栏对应填写每段或每基杆塔工作内容，要求：其填写须具体、明确、相互对应\
                    （7）「确认本工作票1-6项，许可工作开始」，这部分在不同工作票中表述不同，还可能叫做「许可工作内容」\
                    主要表示的是工作的许可情况\
                    要求1：工作负责人签名与（1）中「工作负责人（监护人）」中的负责人为同一人，在检测出非同一人时，应与（9）中「工作负责人变动情况」中变更后的为同一人\
                    要求2：许可时间应在计划工作开始时间之后或者相同时间，特殊情况可以早于计划工作开始时间，但需要在（13）中「备注」内注明原因\
                    要求3:许可方式为：当面通知、电话下达、派人送达三种方式。根据实际通知方式填写完整\
                    要求4:电话下达、派人送达时，工作负责人代写工作许可人姓名。工作许可人在现场时由本人亲自签名\
                    （8）「确认工作负责人布置的工作任务和安全措施」这部分主要需要填写「工作班组人员签名」；要求1：\
                    人数与姓名正确需要同「工作班成员（不包括工作负责人）」中保持一致，如果不一致\
                    检查「工作人员变动情况」是否说明，核对人数与姓名正确（缺少的人员与离去人员姓名相同，多出人员姓名与增添人员姓名相同）\
                    要求2:由本人亲自签名，不允许盖名章或代签。多页工作票只在首页签名。如果使用工作票-工作任务单时，小组负责人在工作票上签名确认，小组人员在各自工作任务单上签名确认\
                    \
                    " + prompt_new()[0]
    
    prompt=f"{luoji_prompt}。现在工人实际填写的工作票内容为：{are}"
    answer_find = "严格参考要求，判断工人实际填写的工作票内容是否符合「要求」\
                    如果没有不符合「要求」的内容，则说无明显错误\
                    如果存在不符合「要求」的内容，请简要、简要回答；回答格式为：'错误，原因'。\
                    错误需要结合工作票的实际情况进行说明\
                    针对要求中每一点进行判断，不符合要求内容的才需要进行罗列说明。\
                    "
                    
    answer = model_answer(prompt, answer_find, tmp=0.001)
    return answer 
    
def prompt_new():
    prompt = "已知「安全规范要求」是：（配电部分）（试行）》（国家电网安质〔2014〕265号）第3.3.12.5条：工作班成员：（1）熟悉工作内容、工作流程，掌握安全措施，\
    明确工作中的危险点，并在工作票上履行交底签名确认手续。第3.4.9条：许可开始工作的命令，应通知工作负责人。其方法可采用：（1）当面许可。工作许可人和工作负责人\
    应在工作票上记录许可时间，并分别签名。第3.5.5条：工作负责人若需长时间离开工作现场时，应由原工作票签发人变更工作负责人，履行变更手续，并告知全体工作班成员\
    及所有工作许可人。原、现工作负责人应履行必要的交接手续，并在工作票上签名确认。第3.5.1条：工作许可后，工作负责人、专责监护人应向工作班成员交待工作内容、\
    人员分工、带电部位和现场安全措施，告知危险点，并履行签名确认手续，方可下达开始工作的命令。第5.2.5.3条：操作人和监护人应根据模拟图或接线图核对所填写的操作项目\
    ，分别手工或电子签名。第15.2.7.2条：用计算机生成或打印的动火工作票应使用统一的票面格式，由工作票签发人审核无误，并手工或电子签名。\
    「安全规范要求」是：工作负责人发出开始工作的命令前，应得到全部工作许可人的许可。\
    已知「安全规范要求」是：开工前，工作负责人或工作票签发人应重新核对现场勘察情况，发现与原勘察情况有变化时，\
    应修正、完善相应的安全措施。实际工作线路名称、杆号应与工作票内容一致，工作负责人到达作业现场应进行现场复勘进行核对。\
    已知「安全规范要求」是： 配合停电的交叉跨越或邻近线路，在线路的交叉跨越或邻近处附近应装设一组接地线。\
    配合停电的同杆（塔）架设线路装设接地线要求与检修线路相同。"

    answer_find = "严格参考要求，判断工人实际填写的工作票内容是否符合「要求」\
                    如果没有不符合「要求」的内容，则说无明显错误\
                    如果存在不符合「要求」的内容，请简要、简要回答；回答格式为：'错误，原因'。\
                    错误需要结合工作票的实际情况进行说明\
                    针对要求中每一点进行判断，不符合要求内容的才需要进行罗列说明。\
                    "
    return prompt,answer_find
