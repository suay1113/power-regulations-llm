# -*- coding: utf-8 -*-
import os, re, time, json, random, copy, shutil, requests
import numpy as np
import pandas as pd
import gradio as gr
import matplotlib
import matplotlib.pyplot as plt

from argparse import ArgumentParser
from datetime import datetime

# from utils.call_ocr import ocr
# from utils.call_api import model_answer
from utils.parse import remove_word, extract_numbers, parse_json, safe_eval
from utils.file_process import random_name, save_base64_images, json_to_history, history_to_json

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("-v", "--version", type=str, default="0.20",
                        help="Demo server name.")
    parser.add_argument("-fp", "--call_port", type=int, default=3535,
                        help="call port for api.")
    
    parser.add_argument("-s", "--save", type=str, default='./cache/demo/',
                        help="save path for annotation files")
    parser.add_argument("-r", "--root-path", type=str, default=None,
                        help="Demo server name.")
    parser.add_argument("--server-name", type=str, default="0.0.0.0",
                        help="Demo server name.")
    parser.add_argument("-p","--server-port", type=int, default=8005,
                         help="Demo server port.")

    args = parser.parse_args()
    return args

class gradioMain():
    def __init_gradio_text__(self):
        # 初始化界面中的文字和样例
                    # <h1 align="center"> <a href="https://www.mininglamp.com/">
                    # <img src="https://www.mininglamp.com/wp-content/themes/minglue/assets/img/logo_blue.png",
                    # alt="logo" border="0" style="margin: 0 auto; height: 80px;"/></a> </h1>
        self.title = """
                    <br>
                    <h1 align="center">工作票测试平台</h1>
                    <br>
                    """
        self.welcome_Message = "<h4> 🎊欢迎使用工作票纠错测试平台🎊 </h4>"

        self.foot = f"""
                    ***
                    研发中 20240930   |  工作票测试平台 内部版本：版本号v{self.version}</n>
                    """  

        self.guides = """
                        * 本平台支持工作票的规则判定
                     """

        self.warning = """
                        1. 按顺序上传多张图片，并点击分析OCR，耗时约10-20s；
                        2. 在右侧查看OCR结果，可适当修改结果；
                        3. 点击对应按钮获取结果
                       """
        
        self.updates =  """
                        #### **工作票-v0.20 更新介绍**
                        1. 功能上线，包括 OCR，规则分析功能
                        """
        
        
        font_path = './files/SourceHanSansCN-Regular.ttf'
        self.simsun_font = matplotlib.font_manager.FontProperties(fname=font_path)  # 加载 SimSun 字体文件
        matplotlib.font_manager.fontManager.addfont(font_path)  # 添加字体到 matplotlib 的字体管理器
        # 设置全局字体
        plt.rcParams['font.family'] = self.simsun_font.get_name()
        plt.rcParams['font.sans-serif'] = [self.simsun_font.get_name()]

        # 其他设定
        self.delete_confirm_js = "(x) => confirm('确认删除当前的内容吗？')"
        self.start_confirm_js = "(x) => confirm('请再次详细检查任务各项参数，确认运行。')"
    
    # gradio核心函数
    def __init__(self, version, save_dictionary, call_port):
        self.version = version
        self.save_dictionary = save_dictionary
        self.api_url = f"http://127.0.0.1:{call_port}"
        self.max_conv = 20
        self.delete_confirm_js = "(x) => confirm('确认删除当前的json吗？')"
        browser_conv_list = []
        
        # 初始化gradio文本信息
        self.__init_gradio_text__()
        # 初始化一些全局变量
        self.frame_path, self.segment_path = None, None
        self.status_flag = gr.State(False)
        self.asr_results = gr.State("")  # 视频的全局的ASR结果
        
        # 初始化gradio界面
        with gr.Blocks(css="footer {visibility: hidden}",
                       theme=gr.themes.Soft(primary_hue=gr.themes.colors.blue,
                                            secondary_hue=gr.themes.colors.sky),
                       title=f"工作票分析-V{self.version}") as self.demo:
            
            task_name = gr.State('')
            files_path = gr.State([])
            # delete_flag = gr.State(False)
            self.demo.load(random_name, [], task_name)

            gr.HTML(self.title)
            with gr.Row(equal_height=True): 
                with gr.Column(scale=3, min_width=300):
                    gr.Markdown(self.welcome_Message)
                with gr.Column(scale=1, min_width=100):
                    with gr.Accordion("🧩 功能介绍", open=False, visible=True):
                        gr.Markdown(self.guides)
                with gr.Column(scale=1, min_width=100):
                    with gr.Accordion("🛎 操作指南", open=False, visible=True):
                        gr.Markdown(self.warning)
                with gr.Column(scale=1, min_width=100):
                    with gr.Accordion("🚀 更新说明", open=False, visible=True):
                        gr.Markdown(self.updates)
                        
            with gr.Accordion( "1️⃣ 上传图片或PDF并OCR", open=True):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=1, min_width=200):
                        upload_file = gr.UploadButton("上传文件", file_count="multiple", variant="primary",
                                                      file_types = ['image', '*.pdf', '*.docx'])
                        parse_btn = gr.Button("解析上传的文件", variant="primary", interactive=False)
                        clean_btn = gr.Button("清空已上传文件", variant="stop", interactive=False)
                        file_exp = gr.FileExplorer(value=None, visible=False, label="已上传文件预览", height=250)
                    with gr.Column(scale=4, min_width=400):
                        image_exp = gr.Gallery(value=None, visible=True, interactive=False, #height=350,
                                               object_fit='contain', label="已上传图片预览",
                                               columns=3 )
                        
            with gr.Accordion("2️⃣ 检查解析情况", open=True):
                parse_cell = gr.Textbox(value=None, interactive=True, lines=5, label="OCR或PDF的解析结果", 
                                        info="对文件的解析结果，为无格式文本，空格回车等错误可忽略。文字识别错误可根据需要进行修改。")
                parse_json_cell = gr.Textbox(value=None, interactive=True, lines=5, label="面向规则的结构化解析结果", 
                                             info="对文件解析结果的二次处理，为后期结构化做好准备。")
            with gr.Accordion("3️⃣ 启动任务与结果查看", open=True):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=1, min_width=150):
                        logic_btn = gr.Button("分析逻辑错误")
                        secure_btn = gr.Button("分析安规错误(开发中)", interactive=False)
                        all_anaysis_btn = gr.Button("同时分析全部错误(开发中)", variant="primary", interactive=False)
                    with gr.Column(scale=4, min_width=400):
                        res_cell = gr.JSON(label="结果输出")
            # with gr.Accordion("4️⃣ 原始结果查看（内部调试）", open=False):
            #     with gr.Row(equal_height=True):
            #         with gr.Column(scale=1, min_width=150):
            #             save_btn = gr.Button("保存结果", interactive=False)
            #         with gr.Column(scale=5, min_width=400):
            #             result_cell = gr.Textbox(value=None, interactive=True, lines=5,
            #                                     label="原始结果", info="大模型输出的原始结果，内部调试可用。")

            gr.Markdown(self.foot)

            upload_file.upload(self.__upload_files, 
                               [files_path, upload_file, task_name],
                               [files_path, image_exp, file_exp, parse_btn, clean_btn])
            parse_btn.click(self.__parse_files, [files_path, task_name], [parse_cell, parse_json_cell])
            clean_btn.click(self.__clean_files, None, 
                            [task_name, files_path, image_exp, file_exp, parse_btn, clean_btn, parse_cell, parse_json_cell])
            logic_btn.click(self.__logic_analysis, [task_name, parse_cell, parse_json_cell], [res_cell])

    # 操作
    def __upload_files(self, files_path, upload_file, task_name):
        save_dir = os.path.join(self.save_dictionary, task_name)
        os.makedirs(save_dir, exist_ok=True)

        if isinstance(upload_file, list):
            for file in upload_file:
                aim_file_path = os.path.join(save_dir, os.path.basename(file))
                shutil.copy(file, aim_file_path)
                if file not in files_path:
                    files_path.append(aim_file_path)
        elif isinstance(upload_file, str):
            file = copy.deepcopy(upload_file)
            aim_file_path = os.path.join(save_dir, os.path.basename(file))
            shutil.copy(file, aim_file_path)
            if file not in files_path:
                files_path.append(aim_file_path)

        print(f"[upload] 获取并保存到文件：{files_path}")

        # 首次记录日志
        log_path = os.path.join(save_dir, f'{task_name}.json')
        log_data = json_to_history(log_path) if os.path.exists(log_path) else {}
        log_data["download"] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "files_path": files_path,
        }
        history_to_json(log_data, log_path, incremental=False)

        return files_path, files_path,\
            gr.FileExplorer(root_dir=save_dir, ignore_glob="**/*.json", visible=True) , \
            gr.update(interactive=True), gr.update(interactive=True)
    
    def __clean_files(self):
        task_name = random_name()
        return task_name, [], None, gr.update(visible=False), \
            gr.update(interactive=False), gr.update(interactive=False), \
            None, None

    def __parse_files(self, files_path, task_name):
        ocr_url = os.path.join(self.api_url, 'ocr-info')
        # JSON 数据
        msg = f"任务名:{task_name}。   开始解析上传的{len(files_path)}个文件，预计需3-15s，请稍后。"
        gr.Info(msg, duration=10)
        json_data = {
            "paths": json.dumps([tmp.replace('../','./') for tmp in files_path])
        }
        response = requests.post(ocr_url, data=json_data).json()   #files=files_payload)

        if response['status'] == 20:
            ocr_res = response['raw_ocr_result']
            ocr_dict_flag, ocr_dict_res = parse_json(response['ticket_data'])
            if not ocr_dict_flag:
                print(f"[parse_files] 结构化存在问题: {ocr_dict_res}")
                ocr_dict_res = eval(response['ticket_data'])
        else:
            msg = f"文件解析失败，任务名：{task_name}，失败原因：{response}。请联系管理员。"
            print(msg)
            gr.Error(msg, duration=5)
            ocr_res, ocr_dict_res = msg, {}

        # 二次记录日志
        log_path = os.path.join(self.save_dictionary, task_name, f'{task_name}.json')
        log_data = json_to_history(log_path) if os.path.exists(log_path) else {}
        log_data["parse"] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ocr_dict_res": ocr_dict_res,
            "ocr_res": ocr_res
        }
        history_to_json(log_data, log_path, incremental=False)
        print(f"[parse_files] 解析完成")

        return ocr_res, ocr_dict_res 

    def __logic_analysis(self, task_name, parse_cell, parse_json_cell):
        ocr_dict_flag, parse_json_cell_ans = parse_json(parse_json_cell)
        if not ocr_dict_flag:
            print(f"[logic_analysis] 结构化存在问题: {parse_json_cell}")
            parse_json_cell_ans = eval(parse_json_cell)
        payload = {'ticket_data': parse_json_cell_ans}

        # 逻辑部分
        logic_url = os.path.join(self.api_url, 'logic-check')
        response = requests.post(logic_url, json=payload).json()
        if response['status'] == 20:
            flag, logic_json = parse_json( response['logic_errors'] )
        else:
            msg = f"逻辑分析失败，任务名：{task_name}，失败原因：{response}。请联系管理员。"
            print(msg)
            gr.Error(msg, duration=5)
            logic_json = {'失败': msg}
        
        # 工人计数部分
        worker_url = os.path.join(self.api_url, 'worker-check')
        response = requests.post(worker_url, json=payload).json()
        if response['status'] == 20:
            flag, worker_json = parse_json( response['worker_errors'])
        else:
            msg = f"工人计数失败，任务名：{task_name}，失败原因：{response}。请联系管理员。"
            print(msg)
            gr.Error(msg, duration=5)
            worker_json = {'失败': msg}

        # 三次记录日志
        log_path = os.path.join(self.save_dictionary, task_name, f'{task_name}.json')
        log_data = json_to_history(log_path) if os.path.exists(log_path) else {}
        log_data["logic_analysis"] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "逻辑结果": logic_json,
            "工人数量分析": worker_json
        }
        history_to_json(log_data, log_path, incremental=False)
        print(f"[logic_analysis] 逻辑处理完成")

        return {"逻辑结果": logic_json, "工人数量分析": worker_json}
        
if __name__ == "__main__":
    GENERATE_TEMPLATE = "\n【系统提示】正在生成答案，2min后将超时。"
    args = parse_args()

    server = gradioMain(version=args.version, 
                        save_dictionary=args.save, 
                        call_port= args.call_port)
    demo = server.demo

    demo.launch(max_threads=5,
                server_port=args.server_port,
                server_name=args.server_name,
                root_path=args.root_path, 
                favicon_path="./files/statics/洞察.png",
                # auth = [('suanyang', '2024@say'), ('rag_test', '2024@rag')],
                auth_message = f"版本号: {args.version}",
                show_api = False
                )
