#!/usr/bin/env python3
"""
reset_root.py — 一键重置 VMware 虚拟机里的 Linux root 密码

原理：
  1. 通过 VMware 内置 VNC 连接到已经用 SystemRescue 应急盘启动的虚拟机
  2. 挂载根分区
  3. 用 chpasswd 重设 root 密码
  4. 读回 shadow 文件验证

前提：
  - 虚拟机已用 SystemRescue 启动，进入 root shell（自动登录）
  - .vmx 里已开启 VNC（RemoteDisplay.vnc.enabled = "TRUE"）

用法：
  python reset_root.py --server 127.0.0.1::5901 --password "你的新密码"
  python reset_root.py --server 127.0.0.1::5901 --password "xxx" --device /dev/sda2

依赖：
  pip install vncdotool
"""

import argparse
import time

from vncdotool import api
from vncdotool.client import VNCDoToolFactory


class ForceCapsFactory(VNCDoToolFactory):
    force_caps = True


def type_text(client, text, delay=0.15):
    for ch in text:
        client.keyPress(ch)
        time.sleep(delay)


def send(client, cmd, wait=3.0):
    type_text(client, cmd)
    client.keyPress("enter")
    time.sleep(wait)


def main():
    parser = argparse.ArgumentParser(description="重置虚拟机 root 密码")
    parser.add_argument("--server", required=True, help="VNC 地址，如 127.0.0.1::5901")
    parser.add_argument("--password", required=True, help="要设置的新密码")
    parser.add_argument("--device", default="/dev/sda2", help="根分区设备，默认 /dev/sda2")
    parser.add_argument("--user", default="root", help="要改的账号，默认 root")
    args = parser.parse_args()

    client = api.connect(args.server, factory_class=ForceCapsFactory)
    time.sleep(0.6)

    print("[1/4] 挂载根分区 %s" % args.device)
    send(client, "mount %s /mnt" % args.device)

    print("[2/4] 确保 %s 账号存在（Ubuntu 有时没开 root）" % args.user)
    # 若 root 行不存在，先补建；useradd 在已存在时会报错但无害
    send(client, "chroot /mnt useradd -m -s /bin/bash %s" % args.user, wait=2.0)

    print("[3/4] 重设 %s 的密码（chpasswd 会自动解锁+设密码）" % args.user)
    cmd = "echo '%s:%s' | chroot /mnt chpasswd" % (args.user, args.password)
    send(client, cmd, wait=3.5)

    print("[4/4] 读回 shadow 验证")
    # 用 grep 只抓目标行，比 sed -n 1p 更稳（账号不一定在第一行）
    send(client, "grep '^%s:' /mnt/etc/shadow" % args.user, wait=2.5)
    client.captureScreen("/tmp/reset_verify.png")
    print("      验证截图已保存 /tmp/reset_verify.png，"
          "确认 %s: 后面是一串 $6$... 或 $y$... 哈希" % args.user)

    print("[4/4] 收尾：卸载并关机")
    send(client, "umount /mnt")
    send(client, "poweroff", wait=2.0)

    client.disconnect()
    print("完成。请删除 .vmx 里的应急盘配置，重新开机后用新密码登录。")


if __name__ == "__main__":
    main()
