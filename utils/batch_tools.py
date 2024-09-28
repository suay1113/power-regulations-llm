import os, random,json
import configparser
import datetime

from utils.file_process import history_to_json, rename_media_in_history




def get_dir_files(root, 
                  allowed_image_types=["jpg", "jpeg", "png", "bmp"],
                  allowed_video_types=["mp4", "avi", "mkv", "mov"]):
    """
    获取指定目录下的文件和子目录，根据允许的文件类型过滤，并将其组织成一个字典。

    Args:
        root (str): 指定的目录路径。
        allowed_image_types (list, optional): 允许的图片类型列表，不包括点号。如果为None，不进行文件类型过滤。默认为None。
        allowed_video_types (list, optional): 允许的视频类型列表，不包括点号。如果为None，不进行文件类型过滤。默认为None。

    Returns:
        dict: 包含目录和文件信息的字典，其中键是目录或文件的名称（不包括后缀），值是与每个目录或文件相关联的路径列表。
    """
    task_total = {}  # 创建一个空字典，用于存储目录和文件的信息
    dir_list = os.listdir(root)  # 列出指定目录中的所有文件和子目录
    allowed_file_types = allowed_video_types + allowed_image_types
    for dir_name in dir_list:  # 遍历所有文件和子目录
        if dir_name.startswith('.'):
            continue
        dir_path = os.path.join(root, dir_name)  # 获取完整的目录路径
        
        if os.path.isfile(dir_path):  # 如果是文件
            if allowed_file_types is None or any(dir_name.lower().endswith(ext) for ext in allowed_file_types):
                # 如果允许的文件类型列表为None或文件名以允许的文件扩展名结尾
                task_total[os.path.splitext(dir_name)[0]] = [dir_path]
        else:  # 如果是目录
            file_list = os.listdir(dir_path)  # 列出子目录中的文件和子目录
            if allowed_image_types is not None:  # 如果允许的文件类型列表不为None
                file_list = [os.path.join(dir_path, tmp) for tmp in file_list if any(tmp.lower().endswith(ext) for ext in allowed_image_types)]
                # 过滤子目录中的文件列表，只保留以允许的文件扩展名结尾的文件
            task_total[dir_name] = file_list  # 将目录名称作为键，文件列表作为值，添加到字典中
    
    return task_total  # 返回包含目录和文件信息的字典

# 计算token数
def sum_usage(usage_dict):
    total_sum = {}
    
    for name, dict in usage_dict.items():
        for key, value in dict.items():
            if key in total_sum:
                total_sum[key] += value
            else:
                total_sum[key] = value
    
    return total_sum

# 计费
def calculate_prices(token_counts):
    # token_counts
    # 定义计价方式（以美元为单位）
    input_price_per_1000_tokens = 0.005  # GPT4-o
    output_price_per_1000_tokens = 0.015

    total_prices = 0.0
    prices_dict = {}

    for file_name, token_info in token_counts.items():
        prompt_tokens = token_info['prompt_tokens']
        completion_tokens = token_info['completion_tokens']
        input_price = (prompt_tokens / 1000) * input_price_per_1000_tokens
        output_price = (completion_tokens / 1000) * output_price_per_1000_tokens
        prices_dict[file_name] = {
            'input_price_usd': round(input_price, 6), 
            'output_price_usd': round(output_price, 6),
            'total_price_usd': round(input_price+output_price, 6),
        }
        total_prices += (output_price + input_price)
    prices_dict.update({'total_price_all_files': round(total_prices, 6)})
    return prices_dict

def get_prices(token_counts):
    # 基于已经有金额的调用计算
    total_prices = 0.0
    prices_dict = {}

    for file_name, token_info in token_counts.items():
        total_cost = token_info['total_cost']
        prices_dict[file_name] = total_cost
        total_prices += total_cost
        
    prices_dict.update({'total_price_all_files': round(total_prices, 6)})
    return prices_dict
    
def generate_json(question_list, image_list=[], video_list=[], frames_list=[], 
                  api_name='gpt4v', 
                  allowed_image_types=["jpg", "jpeg", "png", "bmp"],
                  allowed_video_types=["mp4", "avi", "mkv", "mov"]):
    """
    生成包含问题、图像和视频信息的JSON格式数据。

    Args:
        question_list (list): 包含问题的字符串列表。
        image_list (list, optional): 包含图像文件路径的字符串列表，默认为空列表。
        video_list (list, optional): 包含视频文件路径的字符串列表，默认为空列表。
        frames_list (list, optional): 包含帧图片文件路径的字符串列表，默认为空列表。
        api_name (str, optional): 使用的API名称，默认为 'gpt4v'。
        allowed_image_types (list, optional): 允许的图像文件类型列表，默认为 ["jpg", "jpeg", "png", "bmp"]。
        allowed_video_types (list, optional): 允许的视频文件类型列表，默认为 ["mp4", "avi", "mkv", "mov"]。

    Returns:
        history: 明敬标注平台标准历史格式
        history_usage: 使用的token数目，{'completion_tokens': xxx, 'prompt_tokens': xxx, 'total_tokens': xxx}
    """
    history = []
    history_usage={'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0}   #计量
    
    if len(question_list)== 0 :
        return history, history_usage
        
    for i in range(len(question_list)):
        history.append({"question": question_list[i]})
        if i==0: # 仅在首次对话添加全部媒体文件
            for file_name in image_list:
                if os.path.isfile(file_name):
                    if any(file_name.lower().endswith(ext) for ext in allowed_image_types):
                        if 'image' not in history[0]:
                            history[0]['image'] = [file_name]
                        else:
                            history[0]['image'].append(file_name)
            for file_name in video_list:
                if os.path.isfile(file_name):
                    if any(file_name.lower().endswith(ext) for ext in allowed_video_types):
                        if 'video' not in history[0]:
                            history[0]['video'] = [file_name]
                        else:
                            history[0]['video'].append(file_name)
            for file_name in frames_list:
                if os.path.isfile(file_name):
                    if any(file_name.lower().endswith(ext) for ext in allowed_image_types):
                        if 'frames' not in history[0]:
                            history[0]['frames'] = [file_name]
                        else:
                            history[0]['frames'].append(file_name)
        retry_count = 1                  
        if api_name == 'gpt4v':
            # status_flag, message, result = False, '测试中', {'completion_tokens': 10, 'prompt_tokens': 10, 'total_tokens': 20}
            while retry_count <= 5:
                status_flag, message, result = history_to_gpt4v(history)
                if status_flag:
                    history[-1]['answer'] = message
                    history_usage = sum_usage({'total': history_usage, 'conv': result['usage']})
                    break
                else:
                    wrong_answer = f"【系统提示】答案生成失败。失败原因为 {message}，尝试次数为 {retry_count}。"
                    print(wrong_answer)
                    retry_count += 1
            if not status_flag:
                history[-1]['answer'] = wrong_answer
        elif api_name == 'mingjing':
            while retry_count <= 5:
                status_flag, message, result = history_to_mingjing(history)
                if status_flag:
                    history[-1]['answer'] = message
                    history_usage = sum_usage({'total': history_usage, 'conv': result['usage']})
                    break
                else:
                    wrong_answer = f"【系统提示】答案生成失败。失败原因为 {message}，尝试次数为 {retry_count}。"
                    print(wrong_answer)
                    retry_count += 1
            if not status_flag:
                history[-1]['answer'] = wrong_answer
        else:
            raise f"api_name支持'mingjing'和'gpt4v', 输入为{api_name}"
            
    return history, history_usage 

def batch_infer(root, zip_path, 
                image_SeqAsk_ques_list=[], video_SeqAsk_ques_list=[], scene_SeqAsk_ques_list=[],
                image_RAsk_ques_list=[], video_RAsk_ques_list=[], scene_RAsk_ques_list=[],
                image_RAsk_used_num=0, video_RAsk_used_num=0, scene_RAsk_used_num=0, 
                allowed_image_types=["jpg", "jpeg", "png", "bmp"], allowed_video_types=["mp4", "avi", "mkv", "mov"], api_name='gpt4v'):
    """
    批量进行推理处理，并生成结果。

    Args:
        root (str): 根目录路径，用于保存配置文件和结果。
        zip_path (str): ZIP文件路径，包含了推理所需的问题和文件。
        image_SeqAsk_ques_list (list, optional): 顺序图片问题列表，默认为空列表。
        video_SeqAsk_ques_list (list, optional): 顺序视频问题列表，默认为空列表。
        scene_SeqAsk_ques_list (list, optional): 顺序分镜问题列表，默认为空列表。
        image_RAsk_ques_list (list, optional): 随机图片问题列表，默认为空列表。
        video_RAsk_ques_list (list, optional): 随机视频问题列表，默认为空列表。
        scene_RAsk_ques_list (list, optional): 随机分镜问题列表，默认为空列表。
        image_RAsk_used_num (int, optional): 随机图片问题使用数量，默认为0。
        video_RAsk_used_num (int, optional): 随机视频问题使用数量，默认为0。
        scene_RAsk_used_num (int, optional): 随机分镜问题使用数量，默认为0。
        allowed_image_types (list, optional): 允许的图像文件类型列表，默认为 ["jpg", "jpeg", "png", "bmp"]。
        allowed_video_types (list, optional): 允许的视频文件类型列表，默认为 ["mp4", "avi", "mkv", "mov"]。
        api_name (str, optional): 使用的API名称，默认为 'gpt4v'。

    Returns:
        save_path_list (list): 保存的json路径
        usage_dict (dict): 每个单次对话的history_usage, 二维嵌套dict
    """
    start_time = datetime.datetime.now()  # 任务启动时间
    save_path_list, usage_dict = [], {}  # 保存json的路径、 使用额度的字典
    task_path_dic = get_dir_files(root, allowed_image_types, allowed_video_types)
    task_id = os.path.basename(os.path.normpath(root))
    
    # 记录本次推理的生成log
    config = configparser.ConfigParser()
    config_path = os.path.join(root, 'config.ini')
    # 添加配置信息
    config['info'] = {
        'save_path': root,
        'task_id'  : task_id,
        'zip_file' : zip_path,
        'task_start_time' : start_time.strftime("%Y-%m-%d %H:%M:%S")
    }
    config['questions'] = {
        '必有图片问题': image_SeqAsk_ques_list,
        '必有视频问题': video_SeqAsk_ques_list,
        '必有分镜问题': scene_SeqAsk_ques_list,
        '随机图片问题': image_RAsk_ques_list,
        '随机视频问题': video_RAsk_ques_list,
        '随机分镜问题': scene_RAsk_ques_list,
        '随机图片数目': image_RAsk_used_num,
        '随机视频数目': video_RAsk_used_num,
        '随机分镜数目': scene_RAsk_used_num,
    }
    config['files'] = task_path_dic
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    print("[batch_infer]配置文件已保存为：", config_path)
    
    # 开始推理
    for task_name, task_files in task_path_dic.items():
        print(f"[batch_infer] ===> {task_name}")
        if len(task_files) == 1:
            # 单个文件，可能为图片或者视频
            if any(task_files[0].lower().endswith(ext) for ext in allowed_image_types):
                ans_history, usage = generate_json(image_SeqAsk_ques_list + random.sample(image_RAsk_ques_list, image_RAsk_used_num), 
                                                    image_list=task_files, api_name=api_name)
                ans_history = rename_media_in_history(ans_history, root, root)
                save_path = history_to_json(ans_history, os.path.join(root, task_name))
                save_path_list.append(save_path)
                usage_dict[task_name] = usage
                
            elif any(task_files[0].lower().endswith(ext) for ext in allowed_video_types):
                video_save_path = os.path.join(root, task_name)
                frames_list, segment_list = video_loader_timestamps(task_files[0], n_split=8, max_split=100, sampling='adapt', resize=False)
                
                ans_history, usage = generate_json(video_SeqAsk_ques_list + random.sample(video_RAsk_ques_list, video_RAsk_used_num), 
                                                    video_list=task_files, frames_list=frames_list, api_name=api_name)
                ans_history = rename_media_in_history(ans_history, video_save_path, root)
                save_path = history_to_json(ans_history, os.path.join(video_save_path, task_name+'-video'))
                save_path_list.append(save_path)
                usage_dict[task_name] = usage

                if scene_SeqAsk_ques_list or scene_RAsk_ques_list:
                    for index, segment in enumerate(segment_list):
                        frames_list = video_loader(segment, n_split=2, max_split=10, sampling="adapt")
                        ans_history, usage = generate_json(scene_SeqAsk_ques_list + random.sample(scene_RAsk_ques_list, scene_RAsk_used_num), 
                                                                video_list=[segment], frames_list=frames_list, api_name=api_name)
                        ans_history = rename_media_in_history(ans_history, video_save_path, root)
                        save_path = history_to_json(ans_history, os.path.join(video_save_path, f"{task_name}-scene{index+1:02d}"))
                        save_path_list.append(save_path)
                        usage_dict[task_name] = usage
            else:
                raise f"文件类型不匹配:{task_files}"    
                
        elif len(task_files) > 1:  # 仅支持图片作为多图输入
            ans_history, usage = generate_json(image_SeqAsk_ques_list + random.sample(image_RAsk_ques_list, image_RAsk_used_num), 
                                                    image_list=task_files, api_name=api_name)
            ans_history = rename_media_in_history(ans_history, root, root)
            save_path = history_to_json(ans_history, os.path.join(root, task_name))
            save_path_list.append(save_path)
            usage_dict[task_name] = usage

    # 记录结束时间与任务耗时
    end_time = datetime.datetime.now()
    # 计算任务耗时与成本
    elapsed_time = end_time - start_time
    formatted_elapsed_time = format_timedelta(elapsed_time)
    prices_dict = calculate_prices(usage_dict)
    print(f"\n[batch_infer = {task_id}] 任务启动时间:{start_time.strftime('%Y-%m-%d %H:%M:%S')}; "
          f"任务结束时间:{end_time.strftime('%Y-%m-%d %H:%M:%S')}; 任务持续时间:{formatted_elapsed_time}"
          f"\n[batch_infer = {task_id}] 总价格：{prices_dict['total_price_all_files']:0.4f}$")
    
    # 在现有的配置文件中追加新的内容
    config.set('info', 'task_end_time', end_time.strftime("%Y-%m-%d %H:%M:%S"))  # 在 'info' 部分追加新键值对
    config.set('info', 'task_due_time', formatted_elapsed_time)  # 在 'info' 部分追加新键值对
    config['usage'] = usage_dict
    config['price'] = prices_dict
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    return save_path_list, usage_dict, prices_dict

if __name__ == '__main__':
    from pprint import pprint
    save_path_list, usage, prices = batch_infer('../ipynb/test/',
                                                'text.zip', 
                                                image_SeqAsk_ques_list=[], 
                                                video_SeqAsk_ques_list=['描述这段视频'], 
                                                scene_SeqAsk_ques_list=[],
                                                image_RAsk_ques_list=['描述这张图片', '这个人的妆容是什么样的？'], 
                                                video_RAsk_ques_list=['视频中是否有人物，她在做什么？', '视频的目的是什么？'], 
                                                scene_RAsk_ques_list=['描述这个分镜', '这段分镜在描述什么'],
                                                image_RAsk_used_num=1, video_RAsk_used_num=1, scene_RAsk_used_num=1, 
                                                allowed_image_types=["jpg", "jpeg", "png", "bmp"], allowed_video_types=["mp4", "avi", "mkv", "mov"], 
                                                api_name='gpt4v')
    pprint(save_path_list)
    pprint(usage)
    pprint(prices)
