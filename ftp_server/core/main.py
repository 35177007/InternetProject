#服务器端

import socketserver
import json
import hashlib
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(BASE_DIR)

from core import user_manager as users

# 确定文件路径
users_path = users.users_path
home = r"../files/"

class MyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        """服务器端，数据接收入口"""
        while True:
            try:
                self.data = self.request.recv(1024)  # 接收
                print("客户端地址：", self.client_address)
                print("客户端信息：", self.data)

                cmd_dct = json.loads(self.data.decode("utf-8"))
                action = cmd_dct["action"]
                if hasattr(self, action):
                    func = getattr(self, action)
                    func(cmd_dct)

            except ConnectionResetError as e:
                print(e)
                break

    def logon(self, *args):
        """服务器端，注册接口"""
        cmd_dct = args[0]
        user_path = os.path.join(users_path, cmd_dct["name"] + ".json")
        print(user_path)

        # 验证用户是否存在
        if os.path.exists(user_path):
            print("此用户已经存在")
            res = {
                "status": "-1"
            }
            self.request.send(json.dumps(res).encode("utf-8"))
        else:
            users.add_user(cmd_dct['name'], cmd_dct['password'])
            user = json.load(open(user_path, "r"))
            # 准备用户目录
            self.current = user["name"]
            self.username = user["name"]
            current_path = os.path.join(home, self.current)
            if not os.path.exists(current_path):
                os.mkdir(current_path)

            userinfo = users.getinfo(self.username)
            res = {
                "status": "0",
                "total_size": userinfo["total_size"],
                "used_size": userinfo["total_size"] - userinfo["used_size"]

            }
            self.request.send(json.dumps(res).encode("utf-8"))
            print("注册成功")
            return  # 注册成功返回

    def login(self, *args):
        """服务器端，登陆接口"""
        cmd_dct = args[0]
        user_path = os.path.join(users_path, cmd_dct["name"]+".json")
        print(user_path)

        # 验证用户是否存在
        if os.path.isfile(user_path):
            user = json.load(open(user_path, "r"))

            if cmd_dct["password"] == user["password"]:

                # 准备用户目录
                self.current = user["name"]
                self.username = user["name"]
                current_path = os.path.join(home, self.current)
                if not os.path.exists(current_path):
                    os.mkdir(current_path)

                userinfo = users.getinfo(self.username)

                res = {
                    "status" : "0",
                    "total_size" : userinfo["total_size"],
                    "used_size" : userinfo["total_size"]-userinfo["used_size"]

                }
                self.request.send(json.dumps(res).encode("utf-8"))
                print("登陆成功")


                return  # 登陆成功返回
            else:
                print("密码错误")
        else:
            print("用户不存在")

        res = {
            "status" : "-1"
        }
        self.request.send(json.dumps(res).encode("utf-8"))

    def put(self, *args):
        """服务器端，接收文件"""
        cmd_dct= args[0]
        current_path = os.path.join(home, self.current)
        filename = os.path.join(current_path, cmd_dct["filename"])
        filesize = cmd_dct["size"]

        # 验证用户空间是否足够 确认接收
        userinfo = users.getinfo(self.username)
        if userinfo["total_size"] - userinfo["used_size"] > filesize:
            self.request.send("0".encode("utf-8"))
            print("空间足够")
        else:
            self.request.send("-1".encode("utf-8"))
            print("空间不足")
            return

        # 接收文件内容
        if os.path.isfile(filename):
            file_name = "副本"+cmd_dct["filename"]
            filename = os.path.join(current_path, file_name)
        else:
            filename = filename
        received_size = 0
        m = hashlib.md5()
        with open(filename, "wb") as f:
            while received_size < filesize:
                # 精确控制接收数据大小
                data = self.request.recv(1024)
                f.write(data)
                m.update(data)
                received_size += len(data)

            users.add_used_size(self.username, received_size)
            # MD5值校验
            received_md5 = self.request.recv(1024).decode("utf-8")
            if m.hexdigest() == received_md5:
                print("文件上传成功")
                self.request.send("0".encode("utf-8"))
            else:
                print("文件上传出错")
                self.request.send("-1".encode("utf-8"))

    def get(self, *args):
        """服务器端，发送文件"""
        cmd_dct = args[0]
        current_path = os.path.join(home, self.current)
        filename = os.path.join(current_path, cmd_dct["filename"])

        # 判断文件存在继续
        if os.path.isfile(filename):
            size = os.stat(filename).st_size
            msg_dct = {
                "isfile": True,  # 文件存在
                "filename": filename,
                "size": size,
            }

            # 第一次发送操作文件信息
            self.request.send(json.dumps(msg_dct).encode("utf-8"))
            server_response = self.request.recv(1024)  # 确认接收，防止粘包


            # 接着发送文件内容
            m = hashlib.md5()
            send_size = 0
            with open(filename, "rb") as f:
                while send_size < size:
                    content = f.read(1024)
                    self.request.send(content)
                    m.update(content)
                    send_size += 1024

            time.sleep(1)
            # 增加MD5校验
            self.request.send(m.hexdigest().encode("utf-8"))
            res = self.request.recv(1024).decode("utf-8")
            if res == "0":
                print("文件传输成功")
            else:
                print("文件传输失败")
        else:
            msg_dct = {
                "isfile": False,  # 文件不存在
                "filename": filename,
            }
            # 文件不存在文件信息
            self.request.send(json.dumps(msg_dct).encode("utf-8"))
            print("文件不存在 %s" % filename)

    def rm(self,*args):
        """删除文件"""
        cmd_dct = args[0]
        filename = cmd_dct["filename"]
        current_path = os.path.join(home, self.current)
        file_path = os.path.join(current_path, filename)

        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            os.remove(file_path)
            print('删除{}成功'.format(file_path))
            self.request.send("0".encode("utf-8"))
            users.add_used_size(self.username, -size)
        else:
            print("删除失败")
            self.request.send("-1".encode("utf-8"))

    def ls(self, *args):
        """服务器端，查看当前路径下目录文件"""
        current_path = os.path.join(home, self.current)
        lst = os.listdir(current_path)
        msg_dct = {
            "list":lst
        }
        self.request.send(json.dumps(msg_dct).encode("utf-8"))

    def pwd(self, *args):
        """服务器端，查看当前路径"""
        current = os.getcwd()[:-3]+'files/'+self.current
        msg_dct = {
            "current": current
        }
        self.request.send(json.dumps(msg_dct).encode("utf-8"))

    def mkdir(self, *args):
        """服务器端，创建目录"""
        cmd_dct = args[0]
        dirname = cmd_dct["dirname"]
        current_path = os.path.join(home, self.current)
        dir_path = os.path.join(current_path, dirname)
        os.mkdir(dir_path)
        self.current = dir_path.replace(home, "")
        msg_dct = {
            "current":self.current
        }
        self.request.send(json.dumps(msg_dct).encode("utf-8"))

def run():
    host, port = "localhost", 7001
    server = socketserver.ThreadingTCPServer((host, port), MyHandler)   # 多线程交互
    print("服务器已开启")
    server.serve_forever()


if __name__ == "__main__":
    run()