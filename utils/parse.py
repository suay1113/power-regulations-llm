import os, re, json

def parse_json(input_json):
    if isinstance(input_json, dict):
        return True, input_json
    
    try:
        # Attempt to parse the JSON input
        input_json = input_json.replace("```json","").replace("```","")
        data_dict = json.loads(input_json)
        # Convert lists to newline-separated strings
        # for key, value in data_dict.items():
        #     if isinstance(value, list):
        #         data_dict[key] = '\n'.join(value)
        return True, data_dict  # Return the dictionary and a flag indicating no error
    
    except json.JSONDecodeError as e:
        try:
            data_dict = eval(input_json)
            return True, data_dict
        except Exception as e:
            # Return None and a flag indicating an error occurred
            return False, str(e)

# 格式化耗时为可视化字符串
def format_timedelta(td):
    seconds = td.total_seconds()
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}小时{int(minutes)}分钟{int(seconds)}秒"

def remove_word(string, word_list=[]):
    for word in word_list:
        string = string.replace(word, '')
    return string #.strip()
    
def extract_numbers(s):
    numbers = re.findall(r'\d+', s)
    numbers = [int(num) for num in numbers]
    return numbers[:3]

def safe_eval(data):
    try:
        if isinstance(data, (str, bytes)):
            result = eval(data)
        else:
            result = data
    except TypeError:
        result = data
    return result