# -*- coding: utf-8 -*-
# @Time  :2022/9/25 11:33
# @Author:Clion
# @File  :db_client.py
import json
import sqlite3
import datetime
import queue
import time
from typing import List
from config import DB_PATH


# 连接数据库
class DBClient:

    def __init__(self, db_file=DB_PATH):
        self._con = sqlite3.connect(db_file, check_same_thread=False)  # 创建数据库
        self._cur = self._con.cursor()  # #能获得连接的游标
        self._queue = queue.Queue()
        self._running = False

    def put_sql(self, sql, params=None):  # 实现数据库update、insert、delete的序列化
        self._queue.put((sql, params))
        if not self._running:
            self.ddl_execute()

    def ddl_execute(self):
        while not self._queue.empty():
            self._running = True
            self.execute(*self._queue.get())
        self._running = False
        self.commit()

    def execute(self, sql, params=None):  # 数据增删改查
        if not params:
            params = []
        self._cur.execute(sql, params)

    def fetchall(self):
        return self._cur.fetchall()

    def fetchone(self):  # 查询
        return self._cur.fetchone()

    def commit(self):
        return self._con.commit()

    def rollback(self):
        return self._con.rollback()

    def close(self):
        self._cur.close()
        self._con.close()


class DbConnection:

    def __init__(self, db_file=DB_PATH):
        self.client = DBClient(db_file)

    def insertPayload(self, payload: str):
        try:
            sql = """INSERT OR IGNORE INTO payload_record_t(device_topic,search_key,payload,message_type,key_word,
            message_datetime) VALUES (?,?,?,?,?,?) """
            tm = time.strftime("%Y-%m-%d %H:%M:%S")
            if payload.startswith('+ACK'):
                key_word, _, device_topic, *_, key_data = DbConnection.split_str(payload)
                key_data = key_data[:-1]
                message_type, key_word = key_word.split(':')
                key_data = json.loads(key_data)
                search_key = ""
                for k in key_data.keys():
                    search_key = k
                    break
            else:
                key_word, _, device_topic, *_, key_data = DbConnection.split_str(payload)
                key_data = key_data[:-1]
                message_type, key_word = key_word.split(':')
                key_data = json.loads(key_data)
                search_key = key_data.get("0kb1", list())
                search_key = ";".join(search_key)
            search_key = search_key + ';'
            data_list = [device_topic, search_key, payload, message_type, key_word, tm]
            self.client.execute(sql, data_list)
            self.client.commit()
        except Exception as s:
            print('1', s)

    def searchPayload(self, device_topic: str, keyword: str = '', limit: int | str = 10):
        """
        1. 精确查询：查询abc ab
        :return:
        """
        # sql1 = 'delete from payload_record_t where rowid not in(select max(rowid) from payload_record_t group by ' \
        #        'payload) '  # 数据去重
        # self.client.execute(sql1)
        try:
            limit = int(limit) if isinstance(limit, str) else limit
            sql = """SELECT DISTINCT  device_topic, search_key, payload, message_datetime, message_type, key_word
             FROM payload_record_t WHERE device_topic=?"""
            # sql = """SELECT * FROM payload_record_t WHERE device_topic=?"""
            params = [device_topic]
            if keyword:
                key_word = f'%{keyword.upper()}%'
                search_key = f'%{keyword};%'
                sql = sql + """ AND ((key_word LIKE ? AND message_type='+RESP') OR search_key LIKE ?)"""
                params += [key_word, search_key]
            sql += ' ORDER BY message_datetime DESC LIMIT ?'
            params += [limit]
            self.client.execute(sql, params)
            return self.client.fetchall()[::-1]
        except Exception as s:
            print('2', s)

    def deleteExpiredPayload(self, days=None):
        tm = datetime.datetime.now()
        if days == '1小时前':
            tm2 = str(tm + datetime.timedelta(hours=-1)).split('.')[0]
        elif days == '1天前':
            tm2 = str(tm + datetime.timedelta(days=-1)).split('.')[0]
        elif days == '全部':
            sql_1 = "DELETE FROM payload_record_t;"
            sql_2 = "UPDATE sqlite_sequence SET seq = 0 WHERE name='payload_record_t';"
            self.client.execute(sql_1)
            self.client.execute(sql_2)
            return
        else:
            tm2 = str(tm + datetime.timedelta(days=-3)).split('.')[0]
        sql = "DELETE FROM payload_record_t WHERE message_datetime<=?"
        self.client.execute(sql, [tm2])
        self.client.commit()

    def getCacheData(self, key):
        try:
            sql = "SELECT value FROM cache_data_t WHERE key=?"
            self.client.execute(sql, [key])
            return self.client.fetchone()
        except Exception as s:
            print('3', s)

    def setCacheData(self, key, value):
        try:
            sql = "select * from cache_data_t WHERE key=?"
            self.client.execute(sql, [key])
            # x = list(self.client.fetchone())
            if list(self.client.fetchone()) is not None:
                sql = "UPDATE cache_data_t SET value=? WHERE key=?"
            else:
                sql = "INSERT INTO cache_data_t(value, key) VALUES (?,?)"
            self.client.put_sql(sql, [value, key])
            self.client.commit()
        except Exception as s:
            print('4', s)

    @staticmethod
    def split_str(s: str, sep=',') -> List[str]:
        result = []
        cur = ''
        flag = False  # False表示没有第一次遇见大括号
        for i in s:
            if not flag and i == sep and sep != '':
                result.append(cur)
                cur = ''
            else:
                if not flag and i == '{':
                    flag = True
                cur += i
        else:
            result.append(cur)
        return result


if __name__ == '__main__':
    pass
    # print(*DbConnection().searchPayload('864475040991290', '0x62'), sep='\n')
    # print(*DbConnection.split_str('+RESP:ULK,V001,863940057518519,123132,2333333,
    # 123121,1231321,321321321,004B6,{"0ea1":"41"}$'), sep='\n')
