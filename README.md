# VMware 虚拟机忘记 root 密码？一分钟重置

> 适用于：VMware Workstation / Player 里跑的各种 Linux 虚拟机（Ubuntu / Debian / CentOS 等都行）。
> 原理很简单：借一张应急启动盘，绕过系统直接改掉密码文件。

---

## 一句话原理

虚拟机的硬盘就是本机上的一个大文件。我们**不碰正常系统**，而是用一个「应急系统」（SystemRescue 启动盘）启动虚拟机，然后把正常系统的硬盘「挂载」进来，直接改写里面的密码文件。改完关机、拔掉应急盘、正常开机，密码就变成你设的新密码了。

整个过程**不破坏任何数据**，也不需要知道原密码。

---

## 需要准备什么

1. 一台 Windows 主机（装了 VMware Workstation）
2. 一张应急启动盘镜像：**SystemRescue**（约 1.3 GB，官方免费下载）
3. Python 3（用来做自动化，省去手动敲键盘的麻烦）

---

## 三步走

### 第 1 步：下载应急启动盘

从官方下载 SystemRescue 的 ISO：

```
https://www.system-rescue.org/download/
```

得到一个文件，比如 `systemrescue-13.02-amd64.iso`，记下它的保存路径。

### 第 2 步：让虚拟机从这个应急盘启动

关闭虚拟机，然后修改虚拟机的配置文件（`.vmx` 文件），加几行：

```
sata0:1.present = "TRUE"
sata0:1.deviceType = "cdrom-image"
sata0:1.fileName = "你的ISO完整路径"
sata0:1.startConnected = "TRUE"
bios.bootOrder = "cdrom"
```

> 这五行缺一不可！尤其是 `sata0:1.present` 这一行，少了它应急盘不会被识别。

再打开虚拟机，它就会从应急盘启动，进入一个命令行界面（自动以 root 登录）。

### 第 3 步：挂载硬盘 + 改密码

在应急系统的命令行里依次输入：

```bash
# 找到根分区（一般是 sda2，用下面命令看）
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT

# 挂载根分区
mount /dev/sda2 /mnt

# 改密码（把 新密码 换成你要设的）
echo 'root:新密码' | chroot /mnt chpasswd
```

改完验证一下：

```bash
sed -n 1p /mnt/etc/shadow
```

看到 `root:` 后面是一串 `$6$...` 或 `$y$...` 的乱码（哈希），就说明改好了。

最后收尾：

```bash
umount /mnt
poweroff
```

把 `.vmx` 里刚才加的那几行删掉，重新开机，用新密码登录即可。

---

## 用脚本自动化（可选）

如果你不想手动敲键盘，本仓库提供了一个自动化脚本 `vnc_send.py`，
通过 VMware 内置的 VNC 通道自动向虚拟机注入命令。

前提：在 `.vmx` 里打开 VMware 的内置 VNC：

```
RemoteDisplay.vnc.enabled = "TRUE"
RemoteDisplay.vnc.port = "5901"
```

然后：

```bash
pip install vncdotool paramiko
python vnc_send.py --server 127.0.0.1::5901 --command "mount /dev/sda2 /mnt"
```

---

## 常见坑（都是实战踩过的）

| 坑 | 原因 | 解决办法 |
|---|---|---|
| 改了密码但登录失败 | 键盘注入把大写/数字发错了 | 用 `force_caps=True`（见脚本） |
| 应急盘没启动 | `.vmx` 里少了 `present` 行 | 五行配置补齐 |
| 抢不到 GRUB 菜单 | 部分发行版 GRUB 超时设为 0 | 别抢菜单，直接用应急盘 |
| root 能本机登录但 SSH 上不去 | 系统默认禁止 root 用密码 SSH | 改 sshd_config 的 `PermitRootLogin` |

---

## 安全提醒

- 这只用于**你自己忘了密码的虚拟机**，别用在别人的机器上。
- 改完建议设一个强密码。
- 别把真实密码提交到公开仓库。

---

## 目录结构

```
vmware-root-reset/
├── README.md          # 本说明
├── vnc_send.py        # VNC 键盘注入工具（通用）
├── reset_root.py      # 一键重置 root 密码（封装）
└── LICENSE            # MIT
```
