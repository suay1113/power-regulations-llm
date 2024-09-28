"""
Audio Recognition Tool

这个脚本提供了基于阿里ASR gpu服务调用，速度更快更准确

Author: Suanyang
Date: 2024-07
Content: suanyang@mininglamp.com
"""
import os, time
import requests
import subprocess

from pprint import pprint

def convert_video_to_wav(input_file,
                         output_file='/tmp/tmp.wav'):
    """
    将视频转换为WAV音频并进行语音识别

    输入
        input_file: 输入的MP4文件路径
    :return: 成功标志（True/False）
    """
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",                  # 覆盖无需确认
        "-i", input_file,
        "-ar", "16000",        # 设置音频采样率为16K
        "-ac", "1",            # 设置为单声道
        "-loglevel", "quiet",  # 抑制命令行输出
        output_file
    ]
    
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        return True
    except:
        return False
    
def call_asr_api(wav_path, hot_words=None):
    url = "http://asr-gpu.mlamp.cn/api/asr"
    try:
        start = time.time()
        with open(wav_path, "rb") as f:
            wav_bytes = f.read()
        files = {"file": wav_bytes}
        # data参数可以传递热词 以字符串形式 每个热词以空格分隔
        response = requests.post(url, files=files, data={"hot_word": hot_words}, timeout=90)
        end = time.time()
        
        use_time = round(end - start, 2)
        # print(f"服务用时: {use_time}")
        ans = response.json()
        if ans['code'] == 0:
            return True, ans
        else:
            return False, ans
    except Exception as e:
        return False, str(e)

def merge_sentences(sentences, max_length=50):
    merged_sentences = []
    current_start = round(sentences[0]['start'] / 1000, 1) # 转换为秒
    current_text = ""
    current_end = 0

    for i, sentence in enumerate(sentences):
        sentence_text = sentence['text']
        sentence_end = round(sentence['end'] / 1000, 1) # 转换为秒
        sentence_start = round(sentence['start'] / 1000, 1) # 转换为秒
        
        if len(current_text) + len(sentence_text) <= max_length:
            current_text += sentence_text
            current_end = sentence_end
        else:
            merged_sentences.append({'start': current_start, 'end': current_end, 'text': current_text})
            current_start = sentence_start
            current_text = sentence_text
            current_end = sentence_end

    # 添加最后一个合并的句子
    if current_text:
        merged_sentences.append({'start': current_start, 'end': current_end, 'text': current_text})

    return merged_sentences
    
def video_asr(input_file, hot_words=None, return_type="all"):
    """
    对视频进行语音识别

    :param input_file: 输入的MP4文件路径
    return_type 从['all', 'text', 'sentences_dict', 'sentences_string']可选，分别为原始结构返回，返回字符串，合并时间后的字典或字符串
    :return: 成功标志（True/False），识别结果或失败原因
    """
    wav_file = os.path.splitext(input_file)[0] + ".wav"
    
    convert_video_to_wav(input_file, wav_file)
    flag, ans = call_asr_api(wav_file, hot_words=hot_words)
    if not flag:
        return flag, ans
    if return_type == "all":
        return flag, ans
    elif return_type == "text":
        return flag, ans['text']
    else:
        merged_sentences = merge_sentences(ans['sentences'], max_length=100)
        if return_type == "sentences_dict":
            return flag, merged_sentences
        elif return_type == "sentences_string":
            ans_str = ""
            for ms in merged_sentences:
                ans_str += f"【{ms['start']}】{ms['text']}\n"
            return flag, ans_str
        else:
            return False, "return_type 存在问题"
        
    
if __name__ == "__main__":
    flag, result = video_asr("../examples/test-asr.mp4", return_type="sentences_dict")
    print(flag)
    pprint(result)    

