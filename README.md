## 基于socketserver的简单ftp程序

### 实现功能：
 * 登陆注册
 * 下载/删除服务器文件
 * 上传文件
 * 每个用户有自己的根目录，且只能访问自己的根目录
 * 每个用户有属于自己的磁盘配额，每个用户的可用空间不同
 * 文件传输过程中进度条实时显示（似乎有问题）
 * 允许多用户同时在线
 * 断点续传（待实现）
 * 日志（待实现）
 * 注：尚无法在目录间移动，无法指定文件上传位置

### 启动路径：
- ftp_server/core/user_manager
- ftp_server/bin/server
- ftp_client/bin/client
