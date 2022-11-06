# -*- coding: utf-8 -*-
# @Time  :2022/9/25 11:33
# @Author:Clion
# @File  :db_client.py
import queue
import json
import sqlite3
import datetime
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

    def fetchall(self):  # 从结果中取出所有记录
        return self._cur.fetchall()

    def fetchone(self):  # 从结果中取出一条记录
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

    def insertPayload(self, payload: str, uid: int):
        sql = """INSERT INTO payload_record_t(device_topic,search_key,payload,message_type,key_word,message_datetime,
        uid) VALUES (?,?,?,?,?,?,?) """
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
        self.client.execute(sql, [device_topic, search_key, payload, message_type, key_word, tm, uid])
        self.client.commit()

    def searchPayload(self, device_topic: str, uid: int, keyword: str = '', limit: int | str = 10):
        """
        1. 精确查询：查询abc ab
        :return:
        """
        limit = int(limit) if isinstance(limit, str) else limit
        sql = """SELECT * FROM "payload_record_t" WHERE device_topic=? AND uid=?"""
        params = [device_topic, uid]
        if keyword:
            key_word = f'%{keyword.upper()}%'
            search_key = f'%{keyword};%'
            sql = sql + """ AND ((key_word LIKE ? AND message_type='+RESP') OR search_key LIKE ?)"""
            params += [key_word, search_key]
        sql += ' ORDER BY message_datetime DESC LIMIT ?'
        params += [limit]
        self.client.execute(sql, params)
        return self.client.fetchall()[::-1]

    def deleteExpiredPayload(self, uid: int, days=None):
        tm = datetime.datetime.now()
        if days == '1小时前':
            tm2 = str(tm + datetime.timedelta(hours=-1)).split('.')[0]
        elif days == '1天前':
            tm2 = str(tm + datetime.timedelta(days=-1)).split('.')[0]
        elif days == '全部':
            sql_1 = "DELETE FROM payload_record_t WHERE uid=?"
            # sql_2 = "UPDATE sqlite_sequence SET seq = 0 WHERE name='payload_record_t';"
            self.client.execute(sql_1, [uid])
            # self.client.execute(sql_2)
            self.client.commit()
            return
        else:
            tm2 = str(tm + datetime.timedelta(days=-3)).split('.')[0]
        sql = "DELETE FROM payload_record_t WHERE message_datetime<=? AND uid=?"
        self.client.execute(sql, [tm2, uid])
        self.client.commit()

    def getCacheData(self, key, uid: int):
        sql = "SELECT value FROM cache_data_t WHERE key=? AND uid=?"
        self.client.execute(sql, [key, uid])
        return self.client.fetchone()

    def getLoginData(self):
        sql = "select * from user_t_1 order by username desc limit 1"
        self.client.execute(sql)
        return self.client.fetchone()

    def setCacheData(self, key, value, uid):
        sql = "select count(*) as cnt from cache_data_t WHERE key=? AND uid=?"
        self.client.put_sql(sql, [key, uid])
        if self.client.fetchone()[0] >= 1:
            sql = "UPDATE cache_data_t SET value=? WHERE key=? AND uid=?"
        else:
            sql = "INSERT INTO cache_data_t(value, key, uid) VALUES (?,?,?)"
        self.client.put_sql(sql, [value, key, uid])
        # self.client.commit()

    def setLoginData(self, key, username, password):
        sql = "select count(*) as cnt from user_t_1 WHERE key=? AND username=? AND password=?"
        self.client.put_sql(sql, [key, username, password])
        if self.client.fetchone()[0] < 1:
            #     sql = "UPDATE user_t_1 SET username=? AND password=? WHERE key=?"
            # else:
            sql = "INSERT INTO user_t_1(key, username, password) VALUES (?,?,?)"
        self.client.put_sql(sql, [key, username, password])

    def login(self, username, password):
        sql = "select id, username from user_t where username=? and password=?"
        self.client.execute(sql, [username, password])
        return self.client.fetchone()

    def register(self, username, password):
        sql = "select count(*) as cnt from user_t where username=?"
        self.client.execute(sql, [username])
        if self.client.fetchone()[0] > 0:
            return False
        sql = "INSERT INTO user_t(username, password) values(?, ?)"
        self.client.execute(sql, [username, password])
        self.client.commit()
        return True

    @staticmethod
    def split_str(s: str, sep=',') -> List[str]:
        result = []
        cur = ''
        flag = False  # False表示没有第一次遇见大括号
        for i in s:
            if not flag and i == sep:
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
