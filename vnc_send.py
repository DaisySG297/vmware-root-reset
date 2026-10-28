#!/usr/bin/env python3
"""
vnc_send.py — 通过 VNC 向虚拟机注入键盘命令（含 force_caps 修复）

为什么需要这个脚本：
  用 vncdotool 向 VMware 内置 VNC 注入命令时，默认情况下大写字母和
  特殊符号会被错误编码（大写全变乱、数字错位），导致命令执行失败。
  根因是 vncdotool 需要 force_caps=True 才能正确地把大写字母翻译成
  shift+小写 组合。本脚本封装了这个修复。

用法：
  python vnc_send.py --server 127.0.0.1::5901 --command "ls -la /"
  python vnc_send.py --server 127.0.0.1::5901 --command "echo hi" --capture shot.png

依赖：
  pip install vncdotool
"""

import argparse
import time

from vncdotool import api
from vncdotool.client import VNCDoToolFactory


class ForceCapsFactory(VNCDoToolFactory):
    """开启 force_caps，让大写字母和特殊符号被正确注入。"""
    force_caps = True


def type_text(client, text, delay=0.12):
    """逐字符注入一段文本，每个字符之间留一点间隔，避免丢字。"""
    for ch in text:
        client.keyPress(ch)
        time.sleep(delay)


def send_command(client, cmd, enter_delay=2.0):
    """输入一条命令并回车，等待命令执行。"""
    type_text(client, cmd)
    client.keyPress("enter")
    time.sleep(enter_delay)


def main():
    parser = argparse.ArgumentParser(description="通过 VNC 向虚拟机注入命令")
    parser.add_argument("--server", required=True,
                        help="VNC 地址，例如 127.0.0.1::5901")
    parser.add_argument("--command", required=True, help="要注入的命令")
    parser.add_argument("--delay", type=float, default=0.12,
                        help="每个字符之间的间隔（秒），默认 0.12")
    parser.add_argument("--enter-delay", type=float, default=2.0,
                        help="回车后等待执行的时间（秒），默认 2.0")
    parser.add_argument("--capture", help="执行后截图保存到该路径（可选）")
    parser.add_argument("--clear-first", action="store_true",
                        help="先按 Ctrl+C 清空当前行再输入")
    args = parser.parse_args()

    client = api.connect(args.server, factory_class=ForceCapsFactory)
    time.sleep(0.6)

    if args.clear_first:
        client.keyPress("ctrl-c")
        time.sleep(0.4)

    send_command(client, args.command, enter_delay=args.enter_delay)

    if args.capture:
        client.captureScreen(args.capture)
        print("截图已保存：%s" % args.capture)

    client.disconnect()
    print("命令已注入：%s" % args.command)


if __name__ == "__main__":
    main()
