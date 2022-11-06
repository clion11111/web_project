import datetime
import threading
import time
import ttkbootstrap as ttk
import random
from paho.mqtt import client as mqtt_client
from tkinter import messagebox
from config import Config
from ttkbootstrap.scrolled import ScrolledText
from db_client import DbConnection
from PIL import Image, ImageTk
import webbrowser


class MainFrame(ttk.Window):

    def __init__(self):
        super(MainFrame, self).__init__()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.db = DbConnection()  # 实例化
        self.title('测试平台工具')
        width, height = 1260, 950
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 16
        self.geometry(f'{width}x{height}+{x}+{y}')
        self._set_fault = False  # 是否开启故障巡检区保留故障数据，默认为关闭状态
        self._search_time = None
        self.window_1_true = None
        self.ip = ttk.StringVar()
        self.port = ttk.StringVar()
        self.sub = ttk.StringVar()
        self.key = ttk.StringVar()
        self.imei = ttk.StringVar()
        self.frame1 = ttk.Frame(self)
        self.notebook = ttk.Notebook(self)
        self.frameOne = ttk.Frame(self, relief='ridge', borderwidth=1)  # 消息区
        self.frameTwo = ttk.Frame(self, relief='ridge', borderwidth=1)  # 搜索区
        self.frameThree = ttk.Frame(self, relief='ridge', borderwidth=1)  # 故障巡检区
        self.notebook.grid(row=0, column=1, columnspan=3, sticky=ttk.NSEW)
        self.frame3 = ttk.LabelFrame(self, text="发送区")
        # N/S/E/W分别表示上.下.右.左
        self.frame1.grid(row=0, column=0, sticky=ttk.NSEW)
        self.frameOne.grid(row=0, column=1, sticky=ttk.NSEW)
        self.frameTwo.grid(row=0, column=2, sticky=ttk.NSEW)
        self.frameTwo.grid(row=0, column=3, sticky=ttk.NSEW)
        self.frame3.grid(row=1, column=1, columnspan=3, sticky=ttk.EW)
        self.create()

    def create(self):
        self.create_frame1()
        self.notebook_frame1()
        self.notebook_frame2()
        self.notebook_frame3()
        self.create_frame3()
        self.thread_get_current_time()

    def create_frame1(self):  # 右侧队列
        self.frame1.grid_rowconfigure(1, weight=1)
        self.frame1.grid_rowconfigure(2, weight=1)
        self.frame1.grid_rowconfigure(3, weight=1)
        self.frame1.grid_rowconfigure(4, weight=1)
        """ 版本号 """
        self.contact_us = ttk.Label(self.frame1, text="Mqtt version 1.1.0")
        self.contact_us.grid(row=0, column=0, sticky=ttk.NS)
        self.contact_us.bind("<Enter>", self.callback_near)
        self.contact_us.bind("<Leave>", self.callback_leave)
        self.contact_us.bind("<ButtonPress-1>", self.contact_click)
        """ 连接区域 """  # N/S/W/E分别表示上.下.左.右
        frame_connect = ttk.LabelFrame(self.frame1, text="连接区域")
        frame_connect.grid(row=1, column=0, sticky=ttk.NS)
        ttk.Label(frame_connect, text='I P：').grid(row=0, column=0, sticky=ttk.NS)
        self.ip_entry = ttk.Entry(frame_connect, width=20, textvariable=self.ip)
        self.ip_entry.grid(row=0, column=1, sticky=ttk.NS)
        self.ip.set('81.68.189.102')
        ttk.Label(frame_connect, text='端口：').grid(row=1, column=0, pady=5, sticky=ttk.NS)
        self.post_entry = ttk.Entry(frame_connect, width=20, textvariable=self.port)
        self.post_entry.grid(row=1, column=1, pady=5, sticky=ttk.NS)
        self.port.set('8083')
        self.connect_btn = ttk.Button(frame_connect, text='连接', width=15, command=self.thread_mqtt_connect)
        self.connect_btn.grid(row=2, column=1, pady=10, sticky=ttk.NS)

        """ 订阅区域 """  # N/S/W/E分别表示上.下.左.右
        frame_subscribe = ttk.LabelFrame(self.frame1, text="订阅区域", width=5)
        frame_subscribe.grid(row=2, column=0, sticky=ttk.NS)
        lbl_subscribe = ttk.Label(frame_subscribe, text='订阅：', font=('微软雅黑', 10))
        lbl_subscribe.grid(row=0, column=0, sticky=ttk.NS)
        self.Entry_subscribe = ttk.Entry(frame_subscribe, width=20, textvariable=self.sub)
        self.Entry_subscribe.grid(row=0, column=1, sticky=ttk.NS)
        self.sub.set('VELOTRIC_EB')
        self.But_subscribe = ttk.Button(frame_subscribe, text="订阅", command=self.subscribe, width=15)
        self.But_subscribe.grid(row=1, column=1, pady=10, sticky=ttk.NS)

        """指令区域"""  # N/S/W/E分别表示上.下.左.右
        frame_order = ttk.LabelFrame(self.frame1, text="指令区域", width=5)
        frame_order.grid(row=3, column=0, sticky=ttk.NS)
        lbl_IMEI = ttk.Label(frame_order, text='IMEI：', font=('微软雅黑', 10))
        lbl_IMEI.grid(row=0, column=0, sticky=ttk.NS)
        self.IMEI_Combobox = ttk.Combobox(frame_order, width=18, textvariable=self.key, postcommand=self.search_id)
        self.IMEI_Combobox.grid(row=0, column=1, sticky=ttk.NS)
        self.key_IMEI = Config.IMEI  # 车辆IMEI号
        data = self.db.getCacheData('IMEI')
        if not data:
            key_tc_value = '866760050012956'
        else:
            key_tc_value = data[0]
        self.key.set(key_tc_value)
        lbl_order = ttk.Label(frame_order, text='指令：', font=('微软雅黑', 10))
        lbl_order.grid(row=1, column=0, sticky=ttk.NS)
        self.order = ttk.Combobox(frame_order, width=18, postcommand=self.search_key)
        self.order.grid(row=1, column=1, pady=7, sticky=ttk.NS)
        self.order.bind("<<ComboboxSelected>>", self.go_publish_data)  # 绑定事件,(下拉列表框被选中时，绑定go_publish_data()函数)
        # self.order.bind('<Control-KeyPress-z>', self.show)
        self.data = Config.parity_key
        pub_btn = ttk.Button(frame_order, text="发送", command=self.publish_data, width=15)
        pub_btn.grid(row=2, column=1, pady=10, sticky=ttk.NS)

        """按键区域"""  # N/S/W/E分别表示上.下.左.右
        frame_but = ttk.LabelFrame(self.frame1, text="按键区域", width=5)
        frame_but.grid(row=4, column=0, sticky=ttk.NS)
        unb_btn = ttk.Button(frame_but, text="开锁", command=self.unlocking, width=25)
        unb_btn.grid(row=0, column=0, pady=5, sticky=ttk.NS)
        cap_btn = ttk.Button(frame_but, text="关锁", command=self.shut_key, width=25)
        cap_btn.grid(row=1, column=0, pady=5, sticky=ttk.NS)
        be_btn = ttk.Button(frame_but, text="蓝牙密码计算", command=self.callback_click, width=25)
        be_btn.grid(row=2, column=0, pady=5, sticky=ttk.NS)
        car_btn = ttk.Button(frame_but, text="车辆时间校验", command=self.car_time_check, width=25)
        car_btn.grid(row=3, column=0, pady=5, sticky=ttk.NS)
        mb = ttk.Menubutton(frame_but, text="固件菜单", width=22)  # N/S/W/E分别表示上.下.左.右
        mb.grid(row=4, column=0, pady=5, sticky=ttk.NS)
        menubutton = ttk.Menu(mb, tearoff=False)
        menubutton.add_command(label="查指纹固件", command=self.check_fingerprint)
        menubutton.add_command(label="查询控制器固件", command=self.check_mc)
        menubutton.add_command(label="查询蓝牙固件", command=self.check_bl)
        menubutton.add_command(label="查询VCU固件", command=self.check_vcu)
        menubutton.add_command(label="查询电池固件", command=self.check_bms)
        menubutton.add_command(label="查询Boot固件", command=self.check_boot)
        mb.config(menu=menubutton)
        reboot_btn = ttk.Button(frame_but, text="重启", command=self.reboot_data, width=25)
        reboot_btn.grid(row=5, column=0, pady=5, sticky=ttk.NS)
        fingerprint_btn = ttk.Button(frame_but, text="录指纹", command=self.record_fingerprints, width=25)
        fingerprint_btn.grid(row=6, column=0, pady=5, sticky=ttk.NS)
        factory_settings_btn = ttk.Button(frame_but, text="出厂设置", command=self.factory_settings, width=25)
        factory_settings_btn.grid(row=7, column=0, pady=5, sticky=ttk.NS)

    def notebook_frame1(self):  # 消息区 # N/S/W/E分别表示上.下.左.右
        self.frameOne.grid_rowconfigure(0, weight=1)
        self.frameOne.grid_columnconfigure(0, weight=1)
        self.notebook.add(self.frameOne, text='消息区')
        self.Message_Portion = ScrolledText(self.frameOne, font=('微软雅黑', 10), relief="flat", wrap="word",
                                            cursor='hand2', autohide=True)
        self.Message_Portion.grid(row=0, column=0, sticky=ttk.NSEW)

    def notebook_frame2(self):  # 搜索区 # N/S/W/E分别表示上.下.左.右
        self.frameTwo.grid_rowconfigure(1, weight=1)
        self.frameTwo.grid_columnconfigure(5, weight=1)
        self.notebook.add(self.frameTwo, text='搜索区')
        key_t = ttk.Label(self.frameTwo, text='s_IMEI：', font=('微软雅黑', 10))
        key_t.grid(row=0, column=0, sticky=ttk.NW)
        self.IMEI_KEY = ttk.Combobox(self.frameTwo, width=20, textvariable=self.imei, postcommand=self.search_IMEI)
        self.IMEI_KEY.grid(row=0, column=1, sticky=ttk.NW)
        data = self.db.getCacheData('s_IMEI')
        if not data:
            imei_value = '866760050012956'
        else:
            imei_value = data[0]
        self.imei.set(imei_value)
        key_w = ttk.Label(self.frameTwo, text='内容搜索：', font=('微软雅黑', 11))
        key_w.grid(row=0, column=2, sticky=ttk.NW)
        self.key_ent = ttk.Entry(self.frameTwo, width=16)
        self.key_ent.grid(row=0, column=3, sticky=ttk.NW)
        imei_btn = ttk.Button(self.frameTwo, text="搜索", command=self.search, width=4)
        imei_btn.grid(row=0, column=4, padx=10, sticky=ttk.NW)
        se_btn = ttk.Button(self.frameTwo, text="清除数据库", command=self.clear_data, width=10)
        se_btn.grid(row=0, column=5, padx=20, sticky=ttk.NW)
        ttk.Frame(self.frameTwo).grid(row=0, column=6, sticky=ttk.E + ttk.W)  # N/S/W/E分别表示上.下.左.右
        self.field_of_search = ScrolledText(self.frameTwo, font=('微软雅黑', 10), relief="flat", wrap="word",
                                            cursor='hand2', autohide=True)
        self.field_of_search.grid(row=1, column=0, columnspan=6, sticky=ttk.NSEW)

    def notebook_frame3(self):  # 故障巡检区 # N/S/W/E分别表示上.下.左.右
        self.frameThree.grid_rowconfigure(1, weight=1)
        self.frameThree.grid_columnconfigure(5, weight=1)
        self.notebook.add(self.frameThree, text='故障巡检区')
        self.the_fault_inspection = ttk.Button(self.frameThree, text='开启故障巡检', command=self.set_fault_search,
                                               width=20, cursor='hand2')
        self.the_fault_inspection.grid(row=0, column=0, sticky=ttk.NW)
        key_w = ttk.Label(self.frameThree, text='仅保留设备topic：', font=('微软雅黑', 11))
        key_w.grid(row=0, column=1, padx=20, sticky=ttk.NW)
        self.fa_se = ttk.Combobox(self.frameThree, width=20)
        self.fa_se.grid(row=0, column=2, sticky=ttk.NW)
        self.fa_se['value'] = Config.IMEI
        ttk.Frame(self.frameThree).grid(row=0, column=3, sticky=ttk.W + ttk.E)  # N/S/W/E分别表示上.下.左.右
        self.Inspection_area = ScrolledText(self.frameThree, font=('微软雅黑', 10), relief="flat", wrap="word",
                                            cursor='hand2', autohide=True)
        self.Inspection_area.grid(row=1, column=0, columnspan=6, sticky=ttk.NSEW)
        ttk.Label(self, text='欢迎使用测试平台工具', font=('微软雅黑', 13, 'bold')).grid(row=0, column=2, sticky=ttk.NW)
        self.time_lab = ttk.Label(self, text="%s" % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                                  font=('黑体', 12, 'underline', 'bold'))
        self.time_lab.grid(row=0, column=3, pady=10, sticky=ttk.NE)
        self.after(100, self.uptime)

    def uptime(self):
        self.time_lab.config(text=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.after(200, self.uptime)

    def create_frame3(self):  # 发送区 # N/S/W/E分别表示上.下.左.右
        self.frame3.grid_rowconfigure(0, weight=1)
        self.frame3.grid_columnconfigure(0, weight=1)
        self.send_data = ttk.Text(self.frame3, font=('微软雅黑', 10), height=1, undo=True, highlightbackground='blue')
        self.send_data.grid(row=0, column=0, ipady=40, sticky=ttk.NSEW)
        self.send_data.bind('<Return>', self.bind_send_data)
        self.send_data.bind('<Control-KeyPress-z>', self.undo)
        self.send_data.focus_set()

    def bind_send_data(self, event):  # 绑定回车键
        send_data = self.send_data.get("0.0", "end").strip()
        if send_data != '':
            self.publish_data()
            return 'break'
        else:
            messagebox.showerror('错误', '输入框不能为空！')
            return

    def undo(self, event):  # 撤销
        try:
            self.send_data.edit_redo()
            self.send_data.edit_undo()
        except:
            return

    def get_current_time(self):  # 获取当前时间
        while 1:
            self.get_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            time.sleep(1)

    def thread_get_current_time(self):  # 保持线程在线运行，更新当前时间
        a = threading.Thread(target=self.get_current_time, args=())
        a.daemon = True
        a.start()

    # 连接mqtt服务器
    def connect_mqtt(self):
        client_id = 'python-mqtt-{}'.format(random.randint(0, 1000))
        host = '%s' % self.ip_entry.get().strip()  # 获取ip
        port = int('%s' % self.post_entry.get().strip())  # 获取端口
        try:
            self.client = mqtt_client.Client(client_id, transport="websockets")
            self.client.ws_set_options(path="/mqtt", headers=None)
            self.client.on_connect = self.on_connect
            self.client.connect(host, port, 60)
            self.client.loop_forever()
        except Exception as s:
            messagebox.showerror(title='错误', message='%s，请先连接服务器！' % s)
            self.connect_btn['text'] = '连接'
            self.connect_btn['bootstyle'] = 'primary-outline'
            self.But_subscribe['text'] = '订阅'
            self.But_subscribe['bootstyle'] = 'primary-outline'
            return

    def thread_mqtt_connect(self):
        if self.connect_btn['text'] == '连接':
            connect = threading.Thread(target=self.connect_mqtt, args=())
            connect.start()
            self.connect_btn['text'] = '断开'
            self.connect_btn['bootstyle'] = 'danger-outline'
        else:
            self.connect_btn['text'] = '连接'
            self.connect_btn['bootstyle'] = 'primary-outline'
            self.on_disconnect()
            self.But_subscribe['text'] = '订阅'
            self.But_subscribe['bootstyle'] = 'primary-outline'

    def on_disconnect(self):  # 断开连接
        self.client.disconnect()

    def subscribe(self):  # 订阅
        try:
            sub = self.Entry_subscribe.get().strip()  # 获取订阅主题
            self.client.subscribe(sub)
            self.client.on_message = self.on_message
            if self.thread_mqtt_connect:
                if self.But_subscribe['text'] == '订阅':
                    self.But_subscribe['text'] = '取消订阅'
                    self.But_subscribe['bootstyle'] = 'danger-outline'
                else:
                    self.But_subscribe['text'] = '订阅'
                    self.But_subscribe['bootstyle'] = 'primary-outline'
                    self.unsubscribe()
            if self.connect_btn['text'] == '连接':
                messagebox.showerror('错误', '请先连接客户端！')
                self.But_subscribe['text'] = '订阅'
                self.But_subscribe['bootstyle'] = 'primary-outline'
                return
        except:
            messagebox.showerror('错误', '请先连接客户端！')
            self.But_subscribe['text'] = '订阅'
            self.But_subscribe['bootstyle'] = 'primary-outline'
            return

    def on_connect(self, client, userdata, flags, rc):
        """订阅信息 """
        client.subscribe('VELOTRIC_EB')
        if rc == 0:
            return
        else:
            messagebox.showerror(title='错误', message="Failed to connect, return code %d\n" % rc)
            return

    def unsubscribe(self):  # 取消订阅
        sub = self.Entry_subscribe.get().strip()  # 获取订阅主题
        self.client.unsubscribe(sub)

    def on_message(self, client, userdata, msg):
        """ 接收消息主题 """
        tim = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        payload = str(msg.payload.decode("utf-8"))
        self.db.insertPayload(payload, )  # 存储数据到数据库
        key_word, _, device_topic, _, _, j_data = payload.split(',', maxsplit=5)  # 只解析故障数据
        # j_data = j_data.rstrip('$')
        _, key_word = key_word.split(':')
        key_word = key_word.upper()
        # error_key = '0kb1'
        fa_text = self.fa_se.get().strip()  # 获取仅保留设备topic输入框的值
        # if self._set_fault and key_word == 'ERR' and error_key in json.loads(j_data) and Config.fault_se & set(
        #         json.loads(j_data)[error_key]):
        if self._set_fault and key_word == 'ERR':
            if not fa_text or fa_text == device_topic:
                self.insert_to_error_area(device_topic, payload, tim)

        device_topic = self.IMEI_KEY.get().strip()
        key_value = self.key_ent.get().strip()  # 读取搜索内容输入框的值
        data = self.db.searchPayload(device_topic, key_value)
        if device_topic != "" or key_value != "" in data:  # 自动搜索
            self.auto_refresh()

        self.Message_Portion.insert(ttk.END,
                                    f'\nTopic: {msg.topic}\n{msg.payload.decode("utf-8")}' + '\n' + '消息时间：' + f'{tim}\n')

    def auto_refresh(self):  # 自动刷新
        self.after(100, self.search)

    def search(self):
        search_time = time.time()
        if self._search_time and search_time - self._search_time < 1:
            return
        self._search_time = search_time
        device_topic = self.IMEI_KEY.get().strip()
        self.db.setCacheData('s_IMEI', device_topic)
        key_value = self.key_ent.get().strip()  # 读取搜索内容输入框的值
        data = self.db.searchPayload(device_topic, key_value)
        if not data:
            self.field_of_search.delete(1.0, ttk.END)
            self.field_of_search.insert(ttk.END, f'\n搜索结果: 未搜索到任何消息\n\n')
            self.field_of_search.see(ttk.END)
            return
        self.field_of_search.delete(1.0, ttk.END)
        totalMsg = ""
        for device_topic, search_key, payload, tm, mtype, keyword, in data:
            totalMsg += f'\n搜索结果: {payload}\n消息时间：{tm}\n\n'
        self.field_of_search.insert(ttk.END, totalMsg)
        self.field_of_search.see(ttk.END)

    def insert_to_error_area(self, device, msg, tim):
        msg = f'\n设备topic：{device}\n{msg}\n消息时间{tim}\n\n'
        self.Inspection_area.insert(ttk.END, msg)
        self.Inspection_area.see(ttk.END)
        self.Inspection_area.update()

    def publish_data(self):  # 发送
        if self.But_subscribe['text'] == '取消订阅':
            try:
                device_topic = self.IMEI_Combobox.get().strip()
                self.db.setCacheData('IMEI', device_topic, )
                data = self.send_data.get("0.0", "end").strip()
                d1, d2, d3, d4 = data.split(',', maxsplit=3)
                if d3 == '{{ CURRENT_TIME }}':
                    d3 = time.strftime('%Y%m%d%H%M%S')
                data = f'{d1},{d2},{d3},{d4}'
                pub = 'VELOTRIC_BK_' + '%s' % device_topic
                self.client.publish(pub, payload=data, qos=0)
            except Exception as s:
                messagebox.showerror('错误', f'{s}，请检查指令参数是否有误！')
                return
        else:
            messagebox.showerror('错误', f'请先连接服务器，再订阅！')
            return

    def go_publish_data(self, *args):
        self.send_data.delete(1.0, ttk.END)
        pram = self.order.get().strip()  # 打印选中的值
        d1 = Config.parity.get(pram)
        data = d1 % "{{ CURRENT_TIME }}"
        self.send_data.insert(ttk.END, '%s' % data)
        self.send_data.focus_set()

    def search_id(self):
        s_data = self.key_IMEI
        self.seach_new_id = []
        for i in s_data:
            if self.IMEI_Combobox.get().strip() in i:  # 关键字在该选项中则追加到新的list中
                self.seach_new_id.append(i)
        self.IMEI_Combobox["value"] = self.seach_new_id  # 重新给下拉框赋值

    def search_key(self):
        s_data = self.data
        self.new_data = []
        for i in s_data:
            if self.order.get().strip() in i:  # 关键字在该选项中则追加到新的list中
                self.new_data.append(i)
        self.order["value"] = self.new_data  # 重新给下拉框赋值

    def search_IMEI(self):
        s_data = self.key_IMEI
        self.seach_new_id_ = []
        for i in s_data:
            if self.IMEI_KEY.get().strip() in i:  # 关键字在该选项中则追加到新的list中
                self.seach_new_id_.append(i)
        self.IMEI_KEY["value"] = self.seach_new_id_  # 重新给下拉框赋值

    def set_fault_search(self):  # 故障巡检
        self._set_fault = not self._set_fault
        if self._set_fault:
            self.the_fault_inspection.configure(text='关闭故障巡检')
            self.the_fault_inspection['bootstyle'] = 'danger-outline'

        else:
            self.the_fault_inspection.configure(text='打开故障巡检')
            self.the_fault_inspection['bootstyle'] = 'primary-outline'

    def unlocking(self):  # 开锁
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_CFG=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{"0gc1":"1"}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def shut_key(self):  # 关锁
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_CFG=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{"0gc2":"1"}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def reboot_data(self):  # 重启
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_CMD=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{"0ac8":"1"}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def check_fingerprint(self):  # 查询指纹固件
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_QRY=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{["0ia3"]}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def lu_fingerprint(self):  # 录指纹
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_CMD=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{"0ic2":"fingerprint,0,1"}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def check_mc(self):  # 查询控制器固件版本
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_QRY=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{["0ga5"]}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def check_bl(self):  # 查询蓝牙固件版本
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_QRY=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{["0ca5"]}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def check_vcu(self):  # 查询vcu固件版本
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_QRY=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{["0aa2"]}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def check_bms(self):  # 查询电池固件版本
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_QRY=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{["0ea3"]}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def check_boot(self):  # 查询Boot固件版本
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_QRY=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{["0aa9"]}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def check_upgrade_fail_result(self):  # 查询升级失败结果
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_QRY=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{["0aa8"]}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def car_time_check(self):  # 车辆时间校验
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_CFG=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{"0ab25":"%s"}$' % (self.get_time, self.get_time)
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def factory_settings(self):  # 出厂设置
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_CFG=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{"0ac5":"1"}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def record_fingerprints(self):  # 录指纹
        if self.But_subscribe['text'] == '取消订阅':
            device_topic = self.IMEI_Combobox.get().strip()
            self.db.setCacheData('IMEI', device_topic)
            data = 'AT_CMD=BK,8c16693e2963b129ab210ec13f1ab78b,%s,00770,{"0ic2":"FingerName,0,0"}$' % self.get_time
            pub = 'VELOTRIC_BK_' + '%s' % device_topic
            self.client.publish(pub, payload=data, qos=0)
        else:
            messagebox.showinfo('提示', '请先连接服务器，再订阅！')
            return

    def clear_data(self):  # 清除数据库
        tim = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.db.deleteExpiredPayload('全部')
        self.field_of_search.delete(1.0, ttk.END)
        self.field_of_search.insert(ttk.END, f'\n--数据库数据已全部清除!--\n时间{tim}\n\n')
        self.field_of_search.see(ttk.END)

    def callback_click(self):
        if self.window_1_true is None:
            self.top2 = ttk.Toplevel()
            self.top2.attributes("-topmost", 1)
            width, height = 680, 350
            self.top2.title('计算蓝牙密码')
            self.top2.resizable(False, False)
            x = (self.top2.winfo_screenwidth() - width) // 2
            y = (self.top2.winfo_screenheight() - height) // 4
            self.top2.geometry(f'{width}x{height}+{x}+{y}')
            ttk.Label(self.top2, text='请输入IMEI：', font=('微软雅黑', 13)).grid(row=0, column=0)
            self.be_imei = ttk.Entry(self.top2, width=25, font=('微软雅黑', 12))
            self.be_imei.grid(row=0, column=1)
            ttk.Button(self.top2, text='计算', width=8, command=self.Bluetooth_Password).grid(row=0, column=2, padx=20)
            ttk.Label(self.top2, text='计算结果：', font=('微软雅黑', 12)).grid(row=2, column=0, pady=50)
            self.result_be = ttk.Entry(self.top2, width=25, font=('微软雅黑', 12))
            self.result_be.grid(row=2, column=1)
            self.window_1_true = True
            self.be_imei.focus_set()
            self.top2.protocol('WM_DELETE_WINDOW', self.closed)
            self.top2.mainloop()
        else:
            return

    def Bluetooth_Password(self):  # 蓝牙密码计算
        try:
            self.result_be.delete(0, ttk.END)
            a = self.be_imei.get().strip()
            b = a[::-1]
            dd = int(b[0:4])
            aa = str(dd + 1).rjust(4, '0')
            cc = int(a[-6:-4])
            ccc = int(cc + 1)
            c = 100 - ccc
            be = str(c) + str(aa)
            bea = str(be).rjust(6, '0')
            self.result_be.insert(ttk.END, bea)
        except:
            messagebox.showerror(title='错误', message='请输入有效的IMEI号！')
            return

    def contact_click(self, event):  # Mqtt_versions 说明窗口
        if self.window_1_true is None:
            self.top1 = ttk.Toplevel(resizable=(False, False))
            self.top1.title('版本说明')
            self.top1.attributes("-topmost", 1)
            image = Image.open('./12.png')
            img = ImageTk.PhotoImage(image)
            width, height = 1140, 550
            x = (self.top1.winfo_screenwidth() - width) // 2
            y = (self.top1.winfo_screenheight() - height) // 4
            self.top1.geometry(f'{width}x{height}+{x}+{y}')
            canvas = ttk.Canvas(self.top1, width=image.width, height=image.height, bg='white', cursor="hand2")
            canvas.create_image(0, 0, image=img, anchor="nw")
            canvas.grid(row=0, column=0, sticky=ttk.W)
            ttk.Label(self.top1, text='''
            v1.1.0:
                1、已将空中协议中的全部指令，已转换成快捷指令名称搜索，在本软件指令下拉框
                  中使用，发送前，都会获取当前时间。
                2、在搜索结果区中的内容搜索功能，支持精准搜索和模糊搜索，
                  展示搜索后的10条数据。
                （逻辑——可以独立搜索IMEI号，如果要搜索内容，必须先输入要搜索的IMEI号）
                3、增加了登录，注册功能，目的是为了多开程序后，不会收到重复得数据
                3、清除数据库功能，将用户账号下存储数据全部清除。
                4、在故障巡检区中，开启故障巡检功能，如不选‘仅保留设备topic’
                  则巡检全部在线的，车辆故障。
                5、增加了支持蓝牙密码算法。
                6、发送指令区域，可以自定义指令发送，也可以选择指令下拉框中的指令。
                7、如果发现了Bug或者有什么好的建议可以通过微信和邮箱告诉我！我会逐步完成！
                8、开发这款软件初衷是为了提高工作效率，目前生产平台版本v1.1.0
                9、测试平台与生产平台的区别，开发的主题不一样，连接服务器的方式不一样，
                  测试平台是走的socket，生产平台是走的mqtt，其他的同步！''',
                      font=('微软雅黑', 10), anchor='w').grid(row=0, column=1, sticky=ttk.NSEW)
            # ttk.Label(self.top1, text='邮箱', font=('微软雅黑', 9)).grid(row=1, column=0)
            # N/S/W/E分别表示上.下.左.右
            email_163 = ttk.Entry(self.top1, font=('微软雅黑', 9), width=20)
            email_163.grid(row=1, column=1, pady=5)
            email_163.insert(ttk.END, '15979041557@163.com')
            ttk.Button(self.top1, text='进入163邮箱登录首页', command=self.open_url).grid(row=2, column=1)
            self.window_1_true = True
            self.top1.protocol('WM_DELETE_WINDOW', self.close)
            self.top1.mainloop()
        else:
            return

    def open_url(self):
        webbrowser.open("https://mail.163.com/")

    def close(self):  # 关闭窗口
        self.window_1_true = None
        self.top1.destroy()

    def closed(self):  # 关闭窗口
        self.window_1_true = None
        self.top2.destroy()

    def callback_near(self, event):
        self.contact_us['bootstyle'] = 'danger'

    def callback_leave(self, event):
        self.contact_us['bootstyle'] = 'primary'


if __name__ == "__main__":
    app = MainFrame()
    app.mainloop()
