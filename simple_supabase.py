"""
Простой клиент для Supabase REST API
"""
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

class SimpleSupabase:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def _make_request(self, method: str, table: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None) -> Dict:
        """Выполняет HTTP запрос к Supabase"""
        url = f"{self.url}/rest/v1/{table}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            else:
                return {'error': f'Unknown method: {method}'}
            
            if response.status_code == 200 or response.status_code == 201:
                return response.json() if response.text else {'success': True}
            else:
                return {'error': f'HTTP {response.status_code}: {response.text}'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def select(self, table: str, filters: Optional[Dict] = None) -> List[Dict]:
        """SELECT запрос"""
        params = {}
        if filters:
            for key, value in filters.items():
                params[key] = f'eq.{value}'
        result = self._make_request('GET', table, params=params)
        return result if isinstance(result, list) else []
    
    def insert(self, table: str, data: Dict) -> Dict:
        """INSERT запрос"""
        return self._make_request('POST', table, data=data)
    
    def update(self, table: str, filters: Dict, data: Dict) -> Dict:
        """UPDATE запрос"""
        # Для простоты используем PATCH
        params = {}
        for key, value in filters.items():
            params[key] = f'eq.{value}'
        
        result = self._make_request('PATCH', table, data=data, params=params)
        return result
    
    def delete(self, table: str, filters: Dict) -> Dict:
        """DELETE запрос"""
        params = {}
        for key, value in filters.items():
            params[key] = f'eq.{value}'
        return self._make_request('DELETE', table, params=params)

# Пример использования
if __name__ == '__main__':
    # Тестируем подключение
    client = SimpleSupabase(
        'https://oomxbawrjmqczezdpaqp.supabase.co',
        'sb_secret_yF3kBESRC2YLxW4427qUjQ_gs1hG5LD'
    )
    
    # Тест SELECT
    users = client.select('users', {'user_id': 6495178643})
    print(f'Найдено пользователей: {len(users)}')
