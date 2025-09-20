#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys, os, json, time, shutil, ctypes

ctypes.windll.kernel32.SetConsoleTitleW("GCNAT校园玩便捷认证")

# ------- 自动装 requests -------
try:
    import requests
except ImportError:
    print("正在自动安装 requests …")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests
# ------------------------------

WIDTH = shutil.get_terminal_size().columns
HEIGHT = shutil.get_terminal_size().lines
TOP_HALF = 7

BANNER = (
    "\033[92m"  # 亮绿开始
    r"""
 $$$$$$\   $$$$$$\  $$\   $$\  $$$$$$\  $$$$$$$$\ 
$$  __$$\ $$  __$$\ $$$\  $$ |$$  __$$\ \__$$  __|
$$ /  \__|$$ /  \__|$$$$\ $$ |$$ /  $$ |   $$ |   
$$ |$$$$\ $$ |      $$ $$\$$ |$$$$$$$$ |   $$ |   
$$ |\_$$ |$$ |      $$ \$$$$ |$$  __$$ |   $$ |   
$$ |  $$ |$$ |  $$\ $$ |\$$$ |$$ |  $$ |   $$ |   
\$$$$$$  |\$$$$$$  |$$ | \$$ |$$ |  $$ |   $$ |   
 \______/  \______/ \__|  \__|\__|  \__|   \__|   
  Gingko.c Campus Network Authentication Tool
"""
    "\033[0m"
)

VERSION = "v1.0.1_beta"
NOTICE = [
    "【公告】",
    "1. 仅支持 100.64.x.x 段内网。",
    "2. 若已在线会提示无需重复认证。",
    "3. 自动记录SSID和对应密码，方便下次使用。",
]


def clear():
    os.system("cls" if os.name == "nt" else "clear")


TOP_HALF = 7


def draw_top():
    clear()
    lines_left = [f"\033[92m{l}\033[0m" for l in BANNER.splitlines()]
    lines_right = [f"版本: {VERSION}", ""] + NOTICE

    # 只保留字符画 + 公告，不追加底部文字
    total_left = lines_left
    total_right = lines_right

    sep_col = max(len(l) for l in total_left) + 2
    pad = 0  # 不留上下空白

    # 直接打印内容
    for i in range(len(total_left)):
        left = total_left[i]
        right = total_right[i] if i < len(total_right) else ""
        print(f"{left:<{sep_col - 1}}| {right}")

    # 直接分隔线
    print("=" * WIDTH)


def show_main_menu():
    """显示主菜单"""
    print("\n请选择操作：")
    print("1. 使用保存的账户登录")
    print("2. 使用其他账户登录")
    print("3. 打开工具箱")
    print("0. 退出脚本")
    print("-" * 40)


# -----------------------------



# 以下是校园网认证逻辑
CFG_FILE = "config.json"
SSID_FILE = "ssid_config.json"
LOGIN_URL = "http://110.188.66.35:801/eportal/ "


def get_current_ssid():
    """获取当前连接的WiFi SSID"""
    try:
        if os.name == "nt":  # Windows系统
            # 使用更可靠的方法获取SSID
            result = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                                    capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if result.returncode != 0:
                # 尝试使用系统默认编码
                result = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                                        capture_output=True, text=True)

            lines = result.stdout.split('\n')
            for line in lines:
                if "SSID" in line and "BSSID" not in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        return parts[1].strip()
        else:  # Linux/Mac系统
            # 对于Linux，需要安装wireless-tools
            try:
                result = subprocess.run(["iwgetid", "-r"],
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            except FileNotFoundError:
                # 尝试使用其他方法获取SSID
                try:
                    result = subprocess.run(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
                                            capture_output=True, text=True)
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if line.startswith('yes:'):
                                return line.split(':')[1]
                except FileNotFoundError:
                    pass
    except Exception as e:
        print(f"获取SSID时出错: {e}")
    return None


def check_wifi_connection():
    """检查是否已连接WiFi"""
    ssid = get_current_ssid()
    if not ssid:
        print("❌ 未检测到WiFi连接，请先连接WiFi！")
        return False
    print(f"✅ 已连接到WiFi: {ssid}")
    return True


def get_ip():
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            return ip
    except Exception:
        return None


def is_campus_network():
    """检查是否在校园网环境中（100.64.x.x段）"""
    ip = get_ip()
    if ip and ip.startswith("100.64"):
        return True, ip
    return False, ip


def check_campus_network_auth():
    """检查校园网认证状态"""
    # 首先检查是否在校园网环境中
    is_campus, ip = is_campus_network()
    if not is_campus:
        return False, "❌ 不在校园网环境中，请连接校园WiFi"

    # 检查是否已经通过校园网认证
    try:
        # 尝试访问校园网认证页面会重定向的地址
        r = requests.get("http://baidu.com", timeout=3, allow_redirects=False)

        # 如果重定向到认证页面，说明未认证
        if r.status_code == 302 and "110.188.66.35" in r.headers.get("Location", ""):
            return False, f"✅ 检测到校园网环境(IP: {ip})，需要认证"

        # 如果没有重定向，说明已经认证
        return True, f"✅ 校园网已认证(IP: {ip})，请勿重复认证"

    except requests.exceptions.RequestException:
        return False, f"❌ 网络连接异常，请检查网络(IP: {ip})"


def try_login(username, password, user_ip):
    ts = str(int(time.time() * 1000))
    callback = f"dr{ts}"
    params = {
        "c": "Portal", "a": "login", "callback": callback,
        "login_method": "1", "user_account": f",1,{username}",
        "user_password": password, "wlan_user_ip": user_ip,
        "wlan_user_ipv6": "", "wlan_user_mac": "000000000000",
        "wlan_ac_ip": "182.151.230.105", "wlan_ac_name": "",
        "jsVersion": "3.1", "_": ts,
    }
    headers = {
        "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache", "Pragma": "no-cache",
        "Referer": "http://110.188.66.35/ ",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36 Edg/140.0.0.0",
    }
    try:
        r = requests.get(LOGIN_URL, params=params, headers=headers, timeout=5)
        text = r.text
        if '"result":"1"' in text or '"ret_code":1' in text:
            return True, "✅ 登录成功！"
        if '"ret_code":2' in text:
            return False, "❌ 密码错误或账号不存在。"
        return False, f"❌ 登录失败：{text[:300]}"
    except Exception as e:
        return False, f"❌ 请求异常：{e}"


def input_account():
    while True:
        user = input("请输入校园网账号：").strip()
        pwd = input("请输入校园网密码：").strip()
        if user and pwd:
            return user, pwd
        print("账号或密码不能为空，请重新输入！")


def save_config(username, password):
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump({"username": username, "password": password}, f)


def load_config():
    if os.path.isfile(CFG_FILE):
        try:
            with open(CFG_FILE, encoding="utf-8") as f:
                cfg = json.load(f)
                return cfg["username"], cfg["password"]
        except Exception:
            pass
    return None, None


def save_ssid_config(ssid, username, password):
    """保存SSID对应的账号密码"""
    config = {}
    if os.path.isfile(SSID_FILE):
        try:
            with open(SSID_FILE, encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass

    config[ssid] = {"username": username, "password": password}

    with open(SSID_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_ssid_config(ssid):
    """加载指定SSID的账号密码"""
    if os.path.isfile(SSID_FILE):
        try:
            with open(SSID_FILE, encoding="utf-8") as f:
                config = json.load(f)
                if ssid in config:
                    return config[ssid]["username"], config[ssid]["password"]
        except Exception:
            pass
    return None, None


def main():
    while True:
        draw_top()  # 渲染上半屏（包含公告）

        # 检查校园网认证状态
        auth_status, status_msg = check_campus_network_auth()
        print(status_msg)

        if auth_status:
            # 如果已经认证，显示菜单但不允许登录操作
            print("\n" + "=" * WIDTH)
            print("\n请选择操作：")
            print("0. 退出脚本")
            print("-" * 40)

            choice = input("请选择：").strip()
            if choice == "0":
                print("感谢使用，再见！")
                break
            else:
                print("❌ 无效选择")
                print("按回车键继续...")
                input()
            continue

        print("\n" + "=" * WIDTH)
        show_main_menu()  # 显示主菜单选项

        choice = input("请选择：").strip()

        if choice == "0":
            print("感谢使用，再见！")
            break
        elif choice == "1":
            # 使用保存的账户登录
            username, password = load_config()
            if not username or not password:
                print("❌ 没有保存的账户信息，请先使用选项2登录")
                print("按回车键返回首页...")
                input()
                continue

            # 检查WiFi连接
            if not check_wifi_connection():
                print("按回车键返回首页...")
                input()
                continue

            user_ip = get_ip()
            print(f"当前内网IP：{user_ip}")

            ok, msg = try_login(username, password, user_ip)
            print(msg)

            if ok:
                # 保存SSID对应的账号密码
                current_ssid = get_current_ssid()
                if current_ssid:
                    save_ssid_config(current_ssid, username, password)

            print("按回车键返回首页...")
            input()

        elif choice == "2":
            # 使用其他账户登录
            # 检查WiFi连接
            if not check_wifi_connection():
                print("按回车键返回首页...")
                input()
                continue

            username, password = input_account()
            user_ip = get_ip()
            print(f"当前内网IP：{user_ip}")

            ok, msg = try_login(username, password, user_ip)
            print(msg)

            if ok:
                save_config(username, password)
                # 保存SSID对应的账号密码
                current_ssid = get_current_ssid()
                if current_ssid:
                    save_ssid_config(current_ssid, username, password)

            print("按回车键返回首页...")
            input()
        else:
            print("❌ 无效选择，请重新输入")
            print("按回车键继续...")
            input()


if __name__ == "__main__":
    main()