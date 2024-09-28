import os
import redis
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

class TaskManager:
    # 用于对 task_id 进行全生命周期的维护
    def __init__(self, redis_db: int = 0):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", redis_db))
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)
        self.clear_existing_tasks()

    def record_task(self, task_id: str, task_name: str, args: Optional[List[Any]] = None, kwargs: Optional[Dict[str, Any]] = None):
        # 写入 taskID
        task_details = {
            'task_name': task_name,
            'args': json.dumps(args),
            'kwargs': json.dumps(kwargs),
            'submitted_at': datetime.now().isoformat()
        }
        self.redis_client.hset(f'task:{task_id}', mapping=task_details)

    def remove_task(self, task_id: str):
        # 删除 task
        self.redis_client.delete(f'task:{task_id}')

    def decode_task(self, task_info: Dict[bytes, bytes]) -> Dict[str, Any]:
        # 字节型转字符串并反序列化 JSON 字段
        def bytes_to_str(data):
            if isinstance(data, bytes):
                return data.decode('utf-8')
            if isinstance(data, dict):
                return {bytes_to_str(key): bytes_to_str(value) for key, value in data.items()}
            if isinstance(data, list):
                return [bytes_to_str(item) for item in data]
            return data
        
        decoded_info = bytes_to_str(task_info)
        
        if 'args' in decoded_info:
            decoded_info['args'] = json.loads(decoded_info['args'])
        if 'kwargs' in decoded_info:
            decoded_info['kwargs'] = json.loads(decoded_info['kwargs'])
        
        return decoded_info
        
    def get_all_task_ids(self) -> List[str]:
        # 获取全部 task ID 并按提交时间排序
        keys = self.redis_client.keys('task:*')
        tasks = []

        for key in keys:
            task_info = self.redis_client.hgetall(key)
            decoded_task_info = self.decode_task(task_info)
            task_id = key.decode('utf-8').split(':')[1]
            submitted_at = decoded_task_info.get('submitted_at')
            tasks.append((task_id, submitted_at))

        # 对任务按提交时间进行排序
        tasks.sort(key=lambda x: x[1])
        
        # 只返回任务ID的列表
        sorted_task_ids = [task[0] for task in tasks]
        return sorted_task_ids

    def get_task_details(self, task_id: str) -> Dict[str, Any]:
        # 返回指定 task_id 下的全部内容
        task_key = f'task:{task_id}'
        task_info = self.redis_client.hgetall(task_key)
        return self.decode_task(task_info)

    def clear_existing_tasks(self):
        # 清除所有现有的任务
        keys = self.redis_client.keys('task:*')
        for key in keys:
            self.redis_client.delete(key)
        