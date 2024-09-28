import re, os, cv2, uuid, time, json, copy, base64, hashlib
import zipfile, shutil
from typing import Dict, List
from tqdm import tqdm
from pathlib import Path

def read_base64(file_path):
    with open(file_path, "rb") as file:
        data = file.read()
        data_base64 = base64.b64encode(data).decode("utf-8")
    return data_base64
    
def save_base64_images(image_list: List[str], folder: str):
    os.makedirs(folder, exist_ok=True)
    image_paths = []
    for idx, img_data in enumerate(image_list):
        img_filename = f"image_{(idx+1):02d}.png"
        img_path = os.path.join(folder, img_filename)
        with open(img_path, "wb") as img_file:
            img_file.write(base64.b64decode(img_data))
        image_paths.append(img_path)
    return image_paths
    
def resize_read_image_base64(file_path, max_quality=85, max_size=2, min_size = 512):
    """ 基于file_path路径，获得base64，并保证base64的最大值小于 max_size MB
    输入：
        file_path  (dict): 图像路径
        max_quality (int): 最大base64质量
        max_size (float): 最大base64的空间占用，单位为MB，当过大时会循环降低画质以保证图片小于对应要求 
        min_size (int): 最小边长度
    """
    img = cv2.imread(file_path)
    if img is None:
        raise ValueError (f"[resize_read_image_base64]Invalid image for {file_path}")
    
    height, width, _ = img.shape
    if min(width, height) > min_size:  # 如果最短边大于min_size像素，则按比例缩小图像
        scale_factor = min_size / min(width, height)  # 计算缩放比例
        new_width = int(width * scale_factor)   # 计算新的宽度和高度
        new_height = int(height * scale_factor)
        img = cv2.resize(img, (new_width, new_height))

    # 尝试以当前质量压缩并编码图片
    quality = max_quality  # 设置初始质量
    while quality >= 50:  # 循环，直到Base64图片大小小于2MB或质量降到最低限度
        flag, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if flag:
            base64_image = base64.b64encode(buffer).decode()
            
            if len(base64_image) * 3 / 4 < max_size * 1024 * 1024:   # 检查Base64编码后的大小是否小于2MB
                return base64_image
            else:
                # 如果图片大小大于2MB，降低质量再试
                quality -= 5
        else:
            raise ValueError("[resize_read_image_base64] Invalid encoder for image.")
    
    # 如果退出循环，意味着即使最低质量也无法满足大小要求
    print(f"【resize_read_image_base64】多次压缩后图片仍然大于{max_size}MB，返回质量为{quality}")
    return base64_image


def random_name(custom_word=None):
    # 生成一个唯一的UUID作为文件名的一部分
    unique_filename = str(uuid.uuid4()).split('-')[-1]
    current_datetime = time.strftime("%y%m%d-%H%M%S")  # 获取当前日期时间信息
    # 将UUID和日期时间信息结合起来以创建最终的文件名
    if not custom_word:
        final_filename = f"{current_datetime}_{unique_filename}"
    else:
        final_filename = f"{custom_word}_{current_datetime}_{unique_filename}"
    print("新建任务ID: ", final_filename)
    return final_filename

def make_dir(name, print_flag=True):
    dirname = os.path.dirname(name)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
        if print_flag:
            print(f"未找到保存目录：{dirname}，创建新的文件夹")

def extract_video_segments(file_list):
    video_segments = {}
    # 使用正则表达式匹配文件名中的视频段信息
    pattern = r'(\w+)_(\d+)_(\d+\.\d+)-(\d+\.\d+)\.mp4'
    
    for file_name in sorted(file_list):
        match = re.search(pattern, file_name)
        if match:
            index = int(match.group(2))
            start_time = float(match.group(3))
            end_time = float(match.group(4))
            
            video_segments[index] = (start_time, end_time)
    return video_segments
    
def calculate_md5(file_path: str) -> str:
    """ 计算文件的 MD5 哈希值 """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def match_files(folder1: str, folder2: str) -> Dict[str, List[str]]:
    """ 匹配两个文件夹中相同的文件，并返回匹配成功的文件字典 """
    md5_dict = {}
    matched_files = {}

    # 遍历第一个文件夹
    for root, _, files in os.walk(folder1):
        for file in files:
            if file.endswith('.mp4'):
                file_path = os.path.join(root, file)
                file_md5 = calculate_md5(file_path)
                if file_md5 in md5_dict:
                    print(f"[错误，md5{file_md5}已经存在于md5的dict中] => {file}, {md5_dict[file_md5]}")
                    md5_dict[file_md5].append(file_path)
                else:
                    md5_dict[file_md5] = [file_path]

    # 遍历第二个文件夹
    files = [tmp for tmp in os.listdir(folder2) if tmp.endswith('.mp4')]
    for file in files:
        file_path = os.path.join(folder2, file)
        file_md5 = calculate_md5(file_path)
        if file_md5 in md5_dict:
            md5_dict[file_md5].append(file_path)
        else:
            md5_dict[file_md5] = [file_path]

    # 筛选出匹配的文件
    for md5, paths in tqdm(md5_dict.items()):
        if len(paths) > 1:
            matched_files[md5] = paths

    return matched_files, md5_dict

def match_files_new(folder1: str, folder2: str) -> Dict[str, List[str]]:
    """ 匹配两个文件夹中相同的文件，并返回匹配成功的文件字典 """
    md5_dict = {}
    matched_files = {}

    # 遍历第一个文件夹
    for root, _, files in os.walk(folder1):
        for file in files:
            if file.endswith('.mp4'):
                file_path = os.path.join(root, file)
                file_md5 = calculate_md5(file_path)
                if file_md5 in md5_dict:
                    print(f"[错误，md5{file_md5}已经存在于md5的dict中] => {file}, {md5_dict[file_md5]}")
                    md5_dict[file_md5].append(file_path)
                else:
                    md5_dict[file_md5] = [file_path]

    # 遍历第二个文件夹
    files = [tmp for tmp in os.listdir(folder2) if tmp.endswith('.mp4')]
    for file in files:
        file_path = os.path.join(folder2, file)
        file_md5 = calculate_md5(file_path)
        if file_md5 in md5_dict:
            md5_dict[file_md5].append(file_path)
        else:
            md5_dict[file_md5] = [file_path]

    # 筛选出匹配的文件
    for md5, paths in tqdm(md5_dict.items()):
        if len(paths) > 1:
            matched_files[md5] = paths

    return matched_files, md5_dict
    
def json_to_history(filename):
    """
    从JSON文件读取并将其转换为对话历史列表。

    参数:
        - filename (str): 包含对话历史的JSON文件的文件名。

    返回:
        - history (list): 对话历史列表，每个元素都是一个字典，包含问题、图像、视频和答案等字段。
    """
    with open(filename, 'r', encoding='utf-8') as json_file:
        history = json.load(json_file)
    return history

def history_to_json(history, filename=None, suffix=None, incremental=True):
    """
    将对话历史转换为JSON格式并保存到文件，如果遇到同名文件，会检查内容是否一致。
    
    参数:
        - history (list): 对话历史列表。
        - filename (str, 可选): 保存JSON文件的文件名。如果未提供，则生成随机文件名。
        - suffix (str, 可选): 文件名存在时添加的后缀。
        - incremental (bool, 可选): 是否进行增量更新。默认为True。
    
    返回:
        - filename (str): 保存的JSON文件的文件名。
    """
    if filename is None:
        filename = random_name()
    else:
        if not filename.endswith('.json'):
            filename += '.json'

    # 确保目录存在
    make_dir(filename)

    # 检查文件是否存在且内容是否一致
    if os.path.exists(filename):
        existing_history = json_to_history(filename)
        if history == existing_history:
            # print(f"文件 '{filename}' 已存在且内容一致，无需重复保存。")
            return filename
        elif incremental:
            # 内容不一致，进行增量更新
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(filename):
                new_suffix = f"_{counter}" if suffix is None else f"_{suffix}{counter}"
                filename = base + new_suffix + ext
                counter += 1
                
    # 保存JSON文件
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(history, json_file, ensure_ascii=False, indent=2)
        # print(f"文件 '{filename}' 已成功保存。")

    return filename
    
def rename_frame_list(frame_list):
    ans_list = []
    for frame in frame_list:
        l = frame.split('/')
        if len(l) == 4:
            a,b,c,d = l
            c = c.replace('-adapt', '')
            d = d.split('_')[-1][1:]
            ans_list.append(os.path.join(a,c,d))
        elif len(l) == 3:
            a,b,c = l
            b = b.replace('-adapt', '')
            ans_list.append(os.path.join(a,b,c))
    return ans_list

def copy_images_from_history(history_list, task_name):
    """
    将对话历史中的图片提取出来，并保存到指定文件夹中。

    参数:
        - history_list (list): 包含对话历史的列表，每个元素都是一个字典，包含问题、图像、视频和答案等字段。
        - task_name (str): 任务名

    返回:
        - history_list (list): 包含对话历史的列表，每个元素都是一个字典，包含问题、图像、视频和答案等字段。
    """
    make_dir(task_name)

    total_image_index = 1
    history_list_copy = copy.deepcopy(history_list)
    ans_history = []
    for history in history_list_copy:
        if 'image' in history:
            for index, img in enumerate(history['image']):
                aim_path = f'{task_name}_image{total_image_index}{os.path.splitext(img)[-1]}'
                history['image'][index] = aim_path
                shutil.copy(img, aim_path)
                total_image_index += 1
        if len(history) != 0:
            ans_history.append(history)
    return ans_history

def copy_from_gradio(file_path, save_dir, copy=True):
    """
    将file_path中的文件拷贝到到指定文件夹中。
    并重命名为file_path中路径的uuid
    
    参数:
        - file_path (str): 包含对话历史的列表，每个元素都是一个字典，包含问题、图像、视频和答案等字段。
        - save_dir (str): 保存的路径
        - copy (bool): 是否拷贝，默认为True。False时，即不拷贝仅重新计算路径

    返回:
        - file_path (str): 拷贝后的视频保存路径
    """
    normalized_path = os.path.normpath(os.path.dirname(file_path))
    save_name = os.path.basename(normalized_path)   
    save_path = os.path.join(save_dir, f"{save_name}{os.path.splitext(file_path)[-1]}")
    make_dir(save_path)
    if copy:
        shutil.copy(file_path, save_path)
    return save_path

def rename_media_in_history(history_list, replace_text='None'):
    """
    将对话历史中的图片、视频路径去除 replace_text，从而保证相对路径。

    参数:
        - history_list (list): 包含对话历史的列表，每个元素都是一个字典，包含问题、图像、视频和答案等字段。
        - task_name (str): 任务名
        - replace_text (str): 将history中

    返回:
        - history_list (list): 包含对话历史的列表，每个元素都是一个字典，包含问题、图像、视频和答案等字段。
    """
    history_list_copy = copy.deepcopy(history_list)
    ans_history = []
    for history in history_list_copy:
        for key, value in history.items():
            if key in ["image", "frames", "video"]:
                for index, img in enumerate(value):
                    aim_img = img.replace(replace_text, '')
                    if aim_img.startswith('/'):
                        aim_img = aim_img[1:]
                    value[index] = aim_img
        if len(history) != 0:
            ans_history.append(history)
    return ans_history

def unzip_files(zip_file_path, extracted_path):
    normalized_path = os.path.normpath(extracted_path)
    dir_name = os.path.dirname(normalized_path) 
    folder_name = os.path.basename(normalized_path)
    # 打开ZIP文件
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        names = zip_ref.namelist()  # 获取 ZIP 文件中的所有成员名称
        zip_ref.extractall(dir_name)
    shutil.move

def zip_files(zip_file_path, files_to_compress):
    # 创建一个ZIP文件并添加要压缩的文件
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_to_compress in files_to_compress:
            zipf.write(file_to_compress, os.path.basename(file_to_compress))

def copytree_incremental(src, dst):
    """
    增量复制目录树。

    :param src: 源目录的路径。
    :param dst: 目标目录的路径。如果目标目录已存在，则只复制更新的文件。
    """
    src = Path(src)
    dst = Path(dst)

    for src_dir, _, files in os.walk(src):
        # 计算当前源目录相对于源根目录的相对路径
        relative_path = Path(src_dir).relative_to(src)
        # 创建目标目录中对应的目录
        target_dir = dst / relative_path
        target_dir.mkdir(parents=True, exist_ok=True)

        for file in files:
            src_file = Path(src_dir) / file
            dst_file = target_dir / file

            # 如果目标文件不存在或源文件较新，则复制文件
            if not dst_file.exists() or os.stat(src_file).st_mtime > os.stat(dst_file).st_mtime:
                shutil.copy2(src_file, dst_file)
                
def custom_copy(source, destination):
    """
    复制文件或目录到指定的目标路径。

    :param source: 源文件或目录的路径。
    :param destination: 目标路径。如果源是文件，这可以是新文件的路径或目标目录。如果源是目录，这应该是新目录的路径。
    """
    try:
        if os.path.isfile(source):  # 检查源路径是文件还是目录
            # 确保目标目录存在，如果目标是文件路径，则获取其目录部分
            dest_dir = os.path.dirname(destination) if os.path.dirname(destination) else destination
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)  # 创建目标目录
            shutil.copy2(source, destination)
        elif os.path.isdir(source):
            # 复制目录
            copytree_incremental(source, destination)
    except FileNotFoundError as e:
        print(f"文件或目录未找到: {e}")
    except Exception as e:
        print(f"复制时出错: {e}")

def check_path_list(L):
    for l in L:
        if not os.path.exists(l):
            return False
    return True
    
if __name__ == '__main__':
    history_to_json([{'question': 'hahahah', 'image': 'string', 'video': 'string', 'answer': 'ooo'}],
                     filename = os.path.join('json_file', random_name()))