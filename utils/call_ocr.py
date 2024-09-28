import requests


url = 'http://10.172.28.48:8264/ocr'

def ocr(path):
    try:
        files= {'file': open(path, 'rb')} 
        response = requests.post(url, files=files)
        res = response.json()
        status_code = res['code']
        if status_code == 200:
            return True, ' '.join(res['res']['ocr'])
        else:
            print(f"[OCR错误] {status_code}: {res}")
            return False, res['res']
    except Exception as e:
        print(f"[OCR函数异常] {e}")
        return False, str(e)
    
if __name__ == '__main__':
    flag, ans = ocr("../files/examples/ocr/第1页.jpg")
    print(flag, ans)