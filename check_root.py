#!/usr/bin/env python3
"""
check_root.py — 改密码前，先看看 root 账号是什么状态

很多 Ubuntu 用 autoinstall 装出来，root 压根没设密码（被锁定），
甚至 /etc/shadow 里都没有 root 这一行。直接 chpasswd 可能报错，
或者改了以后还是登不上。所以先跑这个脚本看清楚，再决定怎么改。

前提（同 reset_root.py）：
  - 虚拟机已用 SystemRescue 启动，进入 root shell
  - .vmx 里已开启 VNC（RemoteDisplay.vnc.enabled = "TRUE"）

用法：
  python check_root.py --server 127.0.0.1::5901 --device /dev/sda2

依赖：
  pip install vncdotool
"""

import argparse
import time

from vncdotool import api
from vncdotool.client import VNCDoToolFactory


class ForceCapsFactory(VNCDoToolFactory):
    force_caps = True


def type_text(client, text, delay=0.12):
    for ch in text:
        client.keyPress(ch)
        time.sleep(delay)


def send(client, cmd, wait=2.5):
    type_text(client, cmd)
    client.keyPress("enter")
    time.sleep(wait)


def main():
    parser = argparse.ArgumentParser(description="检查虚拟机里 root 账号状态")
    parser.add_argument("--server", required=True, help="VNC 地址，如 127.0.0.1::5901")
    parser.add_argument("--device", default="/dev/sda2", help="根分区设备，默认 /dev/sda2")
    args = parser.parse_args()

    client = api.connect(args.server, factory_class=ForceCapsFactory)
    time.sleep(0.6)

    print("[1/3] 挂载根分区 %s" % args.device)
    send(client, "mount %s /mnt" % args.device)

    print("[2/3] 查看 /etc/shadow 里 root 这一行")
    # 用 grep 只抓 root 行，比 sed -n 1p 更稳（root 不一定在第一行）
    send(client, "grep '^root:' /mnt/etc/shadow", wait=2.5)
    client.captureScreen("/tmp/check_root.png")
    print("      已截图 /tmp/check_root.png，请看 grep 结果")

    print("[3/3] 判断说明（对照截图）：")
    print("      - 有输出，且 root: 后第二个字段是 ! 或 *  => root 被锁，没密码")
    print("      - 有输出，且第二个字段是 $6$... / $y$... => 已有密码")
    print("      - 完全没有输出                     => root 这一行不存在，需 useradd 补建")

    send(client, "umount /mnt", wait=2.0)
    client.disconnect()
    print("完成。根据上面的结果，决定用 reset_root.py 还是先补建 root 账号。")


if __name__ == "__main__":
    main()
