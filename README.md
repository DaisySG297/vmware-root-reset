# VMware 虚拟机：重置 root 密码 / 开 root

> VMware Workstation / Player 里的 Linux 虚拟机（Ubuntu / Debian / CentOS 等）。实体机请看 [linux-root-reset](https://github.com/DaisySG297/linux-root-reset)。

按情况选一种：

| 你的情况 | 方法 |
|---|---|
| 还能登录 | [场景一](#场景一还能登录开-root--设密码--开-ssh) `sudo passwd root` |
| 密码忘了、登不进去 | [场景二](#场景二密码忘了靠应急盘重置) SystemRescue 应急盘 |

> 提示：Ubuntu 24.04（autoinstall/cloud-init 装的）root 默认**被锁、没密码**，日常靠 sudo 用户管理。所以「改密码」通常 = 「解锁 + 设密码」。

---

## 场景一：还能登录，开 root + 设密码 + 开 SSH

```bash
sudo passwd root        # 输 sudo 密码，再给 root 设新密码（输两遍）
```

报「用户不存在」则先补建：`sudo useradd -m -s /bin/bash root`。

改完密码 SSH 往往还是登不上（Ubuntu 默认禁止 root 密码 SSH），要开的话：

```bash
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sudo systemctl restart ssh        # CentOS/RHEL 用 sshd
```

只是想要 root 权限、不一定要真开 root 账号，用 `sudo -i` 更省事也更安全。

> ⚠️ root + 密码 + 公网 22 端口易被爆破，建议设强密码或只用内网。

---

## 场景二：密码忘了，靠应急盘重置

### 1. 下载 SystemRescue

https://www.system-rescue.org/download/ → 得到 `systemrescue-13.02-amd64.iso`。

### 2. 挂 ISO 到虚拟机并强制从它启动

关闭虚拟机，改 `.vmx` 加几行：

```
sata0:1.present = "TRUE"
sata0:1.deviceType = "cdrom-image"
sata0:1.fileName = "你的ISO完整路径"
sata0:1.startConnected = "TRUE"
bios.bootOrder = "cdrom"
```

> 五行缺一不可，尤其 `sata0:1.present`，少了应急盘不被识别。开机即进应急系统（自动 root 登录）。

### 3. 挂载硬盘 + 改密码

```bash
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT   # 找根分区（一般 sda2）
mount /dev/sda2 /mnt
echo 'root:新密码' | chroot /mnt chpasswd     # 自动解锁+设密码
grep '^root:' /mnt/etc/shadow                # 看到 $6$... / $y$... 即成功
umount /mnt
poweroff
```

> `grep '^root:'` 没输出 = root 不存在，先 `chroot /mnt useradd -m -s /bin/bash root` 再 chpasswd。

重启后删掉 `.vmx` 里刚加的那几行，正常开机。SSH 登不上按场景一开。

---

## 脚本自动化（可选）

不想手动敲键盘，可用本仓库脚本通过 VMware 内置 VNC 注入命令。`.vmx` 里开启 VNC：

```
RemoteDisplay.vnc.enabled = "TRUE"
RemoteDisplay.vnc.port = "5901"
```

```bash
pip install vncdotool paramiko
python vnc_send.py --server 127.0.0.1::5901 --command "mount /dev/sda2 /mnt"
```

---

## 常见坑

| 坑 | 原因 | 解决 |
|---|---|---|
| 键盘注入大写/数字错乱 | VMware VNC 键位映射问题 | 脚本用 `force_caps=True` |
| 应急盘没启动 | `.vmx` 少 `present` 行 | 五行补齐 |
| 改完 root 登不上 | root 默认被锁/不存在 | `sudo passwd root` 或 chpasswd 解锁，缺条目 useradd 补建 |
| root 密码对但 SSH 上不去 | 默认禁止 root 密码 SSH | `PermitRootLogin yes` + `PasswordAuthentication yes` 并重启 ssh |

---

## 安全提醒

只用于你自己忘了密码的机器；改完设强密码；别把真实密码提交到公开仓库。

## 目录结构

```
vmware-root-reset/
├── README.md          # 本说明
├── vnc_send.py        # VNC 键盘注入工具
├── check_root.py      # 改密码前检查 root 状态
├── reset_root.py      # 一键重置 root 密码
└── LICENSE            # MIT
```
