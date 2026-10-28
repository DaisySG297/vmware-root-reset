# VMware 虚拟机：重置 root 密码 / 开启 root 账号

> 适用于：VMware Workstation / Player 里跑的各种 Linux 虚拟机（Ubuntu / Debian / CentOS 等都行）。
>
> 按你的处境选一个：
> - **还能正常登录** → 看「场景一」，开 root + 设密码 + 开 SSH 一条龙；
> - **密码忘了、登不进去** → 看「场景二」，借应急启动盘从外部改密码。
>
> 🔗 **相关仓库**：如果你的机器是**实体机（物理机）**而不是虚拟机，请看 [linux-root-reset](https://github.com/DaisySG297/linux-root-reset)。

---

## 动手前，先搞清楚一件事：root 可能根本没开

很多 Linux 系统（尤其是 **Ubuntu 24.04 用「自动安装 / autoinstall / cloud-init」装出来的**），**root 账号默认是锁定的**——它压根没设密码，日常全靠一个带 sudo 权限的普通用户（安装时填的用户名）来管理。

所以动手前，先想清楚你要改的是**哪个账号**：

| 你的情况 | 该改谁 | 说明 |
|---|---|---|
| 忘了 root 密码，想直接用 root 登录 | root | 但 root 可能被锁，甚至不存在，下面会讲怎么判断 |
| 忘了普通用户（比如 `ubuntu` / 你设的用户名）的密码 | 那个普通用户 | 这个账号通常**一定存在**，直接改它最简单，改完用 `sudo -i` 照样能拿到 root 权限 |

> 💡 **最省事的建议**：如果系统里有普通用户，改普通用户的密码往往比折腾 root 更简单。只有你**明确就是要 root** 时，才需要额外处理「root 没开」这件事。

判断 root 到底什么状态，看一眼 `/etc/shadow` 里 root 那行的第二个字段：

- `!` 或 `*` → root **被锁、没密码**
- `$6$...` / `$y$...` → root **已有密码**
- **压根没有 root 这一行** → root 账号**不存在**

好消息：一条 `chpasswd` / `passwd root` 就能**同时「解锁 + 设密码」**；只有「root 行完全不存在」才需要先 `useradd` 补建。

---

## 场景一：还能正常登录，开 root + 设密码 + 开 SSH

如果你**还能用某个普通用户正常登录**（知道密码、能 sudo），不用任何应急盘，三条命令就能让 root 直接 SSH 登录。

### 1. 开 root 并设密码

```bash
sudo passwd root
```

它先让你输入当前用户的 sudo 密码，再让你给 root 设一个新密码（输两遍）。这一条命令**同时完成「解锁 + 设密码」**。

> 如果报「用户不存在」，说明 `/etc/passwd` 里没 root，先补建再设密码：
> ```bash
> sudo useradd -m -s /bin/bash root
> sudo passwd root
> ```

### 2. 让 root 能通过 SSH 登录

改完密码后，SSH 往往还是登不上——因为 Ubuntu 默认 `PermitRootLogin prohibit-password`（禁止 root 用密码 SSH）。要放开两个开关：

```bash
# 允许 root 用密码 SSH 登录
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config

# 确保密码认证本身是开着的（有些系统会一并关掉）
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

# 重启 SSH 服务让它生效
sudo systemctl restart ssh
```

> 注意服务名：Ubuntu/Debian 是 `ssh`，CentOS/RHEL 是 `sshd`。跑错会提示 `Unit sshd.service not found`，换 `systemctl restart sshd` 即可。

### 3. 验证

```bash
# 从别的机器（或本机）用 root 密码登录
ssh root@你的IP
```

如果还不行，看服务端日志定位真正原因：

```bash
sudo tail -f /var/log/auth.log      # Ubuntu/Debian
sudo tail -f /var/log/secure        # CentOS/RHEL
```

日志关键词：
- `Failed password for root` → 密码不对（回第 1 步重新设）
- `Connection closed by ...` / 无 auth 记录 → 配置没生效（确认重启了服务、改对了文件）

### 配套要点

**只是想要 root 权限，不一定要真的开 root 账号** —— 日常用 `sudo -i` 就能临时切到 root，用完退出，比长期开着一个能密码登录的 root 更安全：

```bash
sudo -i      # 进入 root shell
exit         # 退回普通用户
```

**反向：锁定 root（关闭密码登录）**

```bash
sudo passwd -l root
```

> ⚠️ **安全提醒**：放开 `PermitRootLogin yes` + `PasswordAuthentication yes` 后，root + 密码 + 公网可达的 22 端口很容易被爆破。建议设强密码，或只在内网用（更推荐根本不开 root 密码 SSH，改用 `sudo -i`）。

---

## 场景二：密码忘了、登不进去，靠应急盘重置

> 下面的「三步走」适合你**连普通用户密码都忘了**、只能从外部硬改密码文件的情况。

### 原理

虚拟机的硬盘就是本机上的一个大文件。我们**不碰正常系统**，而是用一个「应急系统」（SystemRescue 启动盘）启动虚拟机，然后把正常系统的硬盘「挂载」进来，直接改写里面的密码文件。改完关机、拔掉应急盘、正常开机，密码就变成你设的新密码了。

整个过程**不破坏任何数据**，也不需要知道原密码。

### 需要准备什么

1. 一台 Windows 主机（装了 VMware Workstation）
2. 一张应急启动盘镜像：**SystemRescue**（约 1.3 GB，官方免费下载）
3. Python 3（用来做自动化，可选）

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

> 还记得开头说的吗？**root 可能没开**。所以改之前先看一眼它的状态，这一步决定了后面要不要补建账号。

在应急系统的命令行里依次输入：

```bash
# 找到根分区（一般是 sda2，用下面命令看）
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT

# 挂载根分区
mount /dev/sda2 /mnt

# 先看一眼 root 现在是什么状态（对应开头那张表）
grep '^root:' /mnt/etc/shadow

# 改密码（把 新密码 换成你要设的；这条命令会自动解锁+设密码）
echo 'root:新密码' | chroot /mnt chpasswd
```

> 如果上一步 `grep '^root:'` **没有任何输出**，说明 root 这一行不存在，先跳到下面「root 不存在怎么办」补建账号，再回来改密码。

改完验证一下：

```bash
grep '^root:' /mnt/etc/shadow
```

看到 `root:` 后面是一串 `$6$...` 或 `$y$...` 的乱码（哈希），就说明改好了。

#### root 这一行完全不存在怎么办（极少数情况）

如果 `grep '^root:' /mnt/etc/shadow` 没有任何输出，说明 `/etc/shadow` 里没有 root 条目。先补建账号（进 chroot 用系统的 useradd）：

```bash
# 在 chroot 环境里补建 root 账号（设好家目录和 shell）
chroot /mnt useradd -m -s /bin/bash root

# 再设密码
echo 'root:新密码' | chroot /mnt chpasswd
```

> 注意：`chroot /mnt chpasswd` 本身就是拿 chroot 里系统的加密算法来算哈希，所以哪怕 root 之前不存在，`useradd` + `chpasswd` 也能一步到位。绝大多数机器用不到这一步。

最后收尾：

```bash
umount /mnt
poweroff
```

把 `.vmx` 里刚才加的那几行删掉，重新开机，用新密码登录即可。

> ⚠️ 重置完成后，**root 可能还是 SSH 登不上**（和场景一第 2 步是同一个坑）。此时你已经能本机登录了，按「场景一」的第 2 步放开 SSH 配置即可。

---

## 用脚本自动化（可选）

如果你不想手动敲键盘，本仓库提供了自动化脚本，通过 VMware 内置的 VNC 通道自动向虚拟机注入命令。

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
| **改完 root 还是登不上** | **系统默认没开 root（被锁或不存在）** | 能登录就 `sudo passwd root`；进不去才用应急盘：`grep '^root:' /mnt/etc/shadow` 看状态，chpasswd 解锁，缺条目 useradd 补建 |
| **root 密码对但 SSH 上不去** | **Ubuntu 默认禁止 root 密码 SSH** | 改 `PermitRootLogin yes` + `PasswordAuthentication yes` 并重启 ssh（见场景一第 2 步） |

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
├── check_root.py      # 改密码前先检查 root 账号状态
├── reset_root.py      # 一键重置 root 密码（封装）
└── LICENSE            # MIT
```
