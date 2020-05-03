
# 客户端

import socket
import os
import json
import hashlib
import time
import random

class FtpClient(object):
    def __init__(self,):
        self.client = socket.socket()

    def connect(self, ip, port):
        self.client.connect((ip, port))

    def logon(self):
        name = input("\033[33;1m请输入用户名：\033[0m").strip()
        password = input("\033[33;1m请输入密码：\033[0m").strip()
        infos = {
            "action": "logon",
            "name": name,
            "password": password
        }

        # 发送用户信息进行认证
        self.client.send(json.dumps(infos).encode("utf-8"))

        # 判断返回信息
        res = json.loads(self.client.recv(1024).decode("utf-8"))
        if res["status"] == "0":
            print("\033[34;1m注册成功\033[0m")
            print("\033[35;1m总大小为: \t%.2f MB \t(%d B)\033[0m" % (res["total_size"] / 1024 ** 2, res["total_size"]))
            print("\033[35;1m可用空间为: \t%.2f MB \t(%d B)\033[0m" % (res["used_size"] / 1024 ** 2, res["used_size"]))
            self.help()
            self.interactive()
        else:
            print("\033[34;1m注册失败\033[0m")

    def login(self):
        """用户登录"""
        name = input("\033[32;1m请输入用户名：\033[0m").strip()
        password = input("\033[32;1m请输入密码：\033[0m").strip()
        infos = {
            "action": "login",
            "name": name,
            "password": password
        }

        # 发送用户信息进行认证
        self.client.send(json.dumps(infos).encode("utf-8"))

        # 判断返回信息
        res = json.loads(self.client.recv(1024).decode("utf-8"))
        if res["status"] == "0":
            print("\033[34;1m登陆成功\033[0m")
            print("\033[35;1m总大小为: \t%.2f MB \t(%d B)\033[0m" % (res["total_size"] / 1024 ** 2,res["total_size"]))
            print("\033[35;1m可用空间为: \t%.2f MB \t(%d B)\033[0m" % (res["used_size"] / 1024 ** 2, res["used_size"]))
            self.help()
            self.interactive()
        else:
            print("\033[34;1m登陆失败\033[0m")

    def interactive(self):
        """用户交互"""
        while True:
            cmd = input(">>>")
            # 输入为空，继续等待用户输入
            if len(cmd)==0 :continue
            action = cmd.split(" ")[0]

            # 反射，通过函数名字符串获取函数地址，便于扩展
            if hasattr(self, "%s" % action):
                func = getattr(self, "%s" % action)
                func(cmd)
            else:
                self.help()

    def put(self, *args):
        """客户端，发送文件"""
        cmd_split = args[0].split(" ")
        if len(cmd_split)>1:
            filename = os.path.join(r'../send/', cmd_split[1])

            # 判断文件是否存在，存在则继续
            if os.path.isfile(filename):
                size = os.stat(filename).st_size  # 获取文件大小
                msg_dct = {
                    "action": "put",
                    "filename": cmd_split[1],
                    "size": size,
                    "override": True
                }

                # 第一次发送操作文件信息
                self.client.send(json.dumps(msg_dct).encode("utf-8"))

                # 确认接收，防止粘包，确认服务器空间是否足够
                server_response = self.client.recv(1024).decode("utf-8")
                if server_response == "0":
                    print("\033[34;1m空间足够\033[0m")
                else:
                    print("\033[34;1m空间不足\033[0m")
                    return  # 中断操作

                # 接着发送文件内容
                m = hashlib.md5()
                send_size = 0
                with open(filename,"rb") as f:
                    while send_size < size:
                        content = f.read(1024)
                        self.client.send(content)
                        m.update(content)
                        send_size+=1024
                        per = int(send_size/size)*100
                        print('\r{}{}%'.format('*'*int(per/2),per), end='', flush=True)


                time.sleep(1)
                # 可以增加MD5校验
                self.client.send(m.hexdigest().encode("utf-8"))
                res = self.client.recv(1024).decode("utf-8")
                if res == "0":
                    print("\033[34;1m\n文件传输成功\033[0m")
                else:
                    print("\033[34;1m文件传输失败\033[0m")
            else:
                print("\033[32;1m文件：%s不存在[0m" % filename)
        else:
            print("\033[34;1m输入错误\033[0m")

    def get(self, *args):
        """客户端，接收文件"""
        cmd_split = args[0].split(" ")
        if len(cmd_split) > 1:
            filename = cmd_split[1]
            msg_dct = {
                "action": "get",
                "filename": filename
            }

            # 第一次发送操作文件信息
            self.client.send(json.dumps(msg_dct).encode("utf-8"))

            # 接收文件状态，是否存在和文件大小
            server_response = self.client.recv(1024)
            server_dct = json.loads(server_response.decode("utf-8"))

            if server_dct["isfile"]:  # 文件存在
                self.client.send(b"200 ok")  # 确认接收

                # 接收文件内容
                m = hashlib.md5()
                current_path = r"../rec"
                filename = os.path.join(current_path, filename)
                data_size = server_dct["size"]
                received_size = 0
                with open(filename, "wb") as f:
                    while received_size < data_size:
                        # 精确控制接收数据大小
                        data = self.client.recv(1024)
                        f.write(data)
                        m.update(data)
                        received_size += len(data)
                        per = int(received_size / data_size) * 100
                        print('\r{}{}%'.format('*' * int(per / 2), per), end='', flush=True)

                # 接收MD5校验
                received_md5 = self.client.recv(1024).decode("utf-8")
                if m.hexdigest() == received_md5:
                    print("\033[34;1m\n文件下载成功\033[0m")
                    self.client.send("0".encode("utf-8"))
                else:
                    print("\033[34;1m\n文件下载失败\033[0m")
                    self.client.send("-1".encode("utf-8"))
            else:
                print("\033[34;1m\n文件不存在\033[0m")

    def rm(self, *args):
        """删除文件"""
        cmd_split = args[0].split(" ")
        if len(cmd_split) > 1:
            filename = cmd_split[1]
            msg_dct = {
                "action": "rm",
                "filename": filename
            }
        # 第一次发送操作文件信息
        self.client.send(json.dumps(msg_dct).encode("utf-8"))

        # 是否删除成功
        res = self.client.recv(1024).decode("utf-8")
        if res == "0":
            print("\033[34;1m删除成功\033[0m")
        else:print("\033[34;1m删除失败\033[0m")

    def ls(self, *args):
        """客户端，查看文件目录"""
        msg_dct = {
            "action": "ls"
        }
        # 第一次发送操作文件信息
        self.client.send(json.dumps(msg_dct).encode("utf-8"))

        # 接收文件状态，是否改变成功
        server_response = self.client.recv(1024)
        server_dct = json.loads(server_response.decode("utf-8"))
        for line in server_dct["list"]:
            print("\033[34;1m{}\033[0m".format(line),end='    ')
        print('\n')

    def exit(self, *args):
        """退出客户端"""
        exit()

    def pwd(self, *args):
        """客户端，查看当前路径"""
        msg_dct = {
            "action": "pwd"
        }
        # 第一次发送操作文件信息
        self.client.send(json.dumps(msg_dct).encode("utf-8"))

        # 接收文件状态，是否改变成功
        server_response = self.client.recv(1024)
        server_dct = json.loads(server_response.decode("utf-8"))

        print(server_dct["current"])

    def mkdir(self, *args):
        """客户端，创建文件目录"""
        cmd_split = args[0].strip().split(" ")
        if len(cmd_split) > 1:
            dirname = cmd_split[1]
            msg_dct = {
                "action": "mkdir",
                "dirname": dirname
            }
            # 第一次发送操作文件信息
            self.client.send(json.dumps(msg_dct).encode("utf-8"))

            # 接收文件状态，是否创建成功
            server_response = self.client.recv(1024)
            server_dct = json.loads(server_response.decode("utf-8"))

            print(server_dct["current"])

    def help(self,*args):

        msg = """\033[32;1m
               ------------可用命令------------
               ls              显示我的目录下文件
               pwd             显示当前文件路径
               get filename    下载指定文件
               put filename    上传指定文件
               mkdir filename  创建目录
               rm filename     删除指定文件
               exit            退出
               \033[0m"""
        print(msg)

def run():
    """启动客户端"""
    myftp = FtpClient()
    myftp.connect("localhost", 7001)
    print('\033[33;1m1.登陆\t2.注册\033[0m')
    chi = input(">>>")
    if chi == '1': myftp.login()
    elif chi == '2': myftp.logon()
    else: print("\033[34;1m指令错误\033[0m")

if __name__ == "__main__":
    run()