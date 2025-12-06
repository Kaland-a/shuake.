# Copyright 2025 BlackCyan (Modified for DGUT LMS)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import msvcrt
import os
import re
import sys
import time

import requests
from DrissionPage import Chromium, ChromiumPage, ChromiumOptions
from DrissionPage.common import Actions
from DrissionPage.errors import ElementNotFoundError

_author = '墨青BlackCyan (Modified for DGUT)'
_name = 'DGUT LMS自动答题脚本'
_version = '1.3.2-dgut'
menu = [
    '1.自动答题',
    '2.反馈',
    '0.退出脚本'
]

current_file = os.path.abspath(sys.executable)  # 如果没有打包直接运行,则参数应改为 __file__
current_dir = os.path.dirname(current_file)
config_dir = os.path.join(current_dir, 'config')
config_file = os.path.join(config_dir, 'DGUT_LMS.json')


def check_config():
    """检查配置文件"""
    # 检查配置文件夹是否存在
    if not os.path.exists(config_file):
        os.makedirs(config_dir, exist_ok=True)

        # 配置文件模板
        config_template = {
            'browser_path': 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_template, f, ensure_ascii=False, indent=2)

        print(f'配置文件不存在,已为您创建配置文件: {config_file}')


def check_browser():
    """检查浏览器"""
    co = ChromiumOptions()
    dp_debug = None

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    co.set_browser_path(config['browser_path']).save()

    browser_path = co.browser_path

    print('正在检查浏览器文件配置...')
    print(f'读取到浏览器文件配置: {browser_path}')

    if not os.path.exists(browser_path) or not os.path.isfile(browser_path):
        raise FileNotFoundError(f'配置中的浏览器可执行文件位置为 {browser_path}, 但该文件不存在。')

    try:
        dp_debug = ChromiumPage(1234)
    except FileNotFoundError as why:
        raise FileNotFoundError(f'尝试启动浏览器失败: {why}')
    finally:
        if dp_debug:
            dp_debug.close()


def set_browser(browser_path):
    """设置浏览器"""
    if not os.path.exists(browser_path) or not os.path.isfile(browser_path):
        raise FileNotFoundError(f"文件不存在: {browser_path}")

    # 保存浏览器配置
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
        config['browser_path'] = browser_path

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"浏览器路径设置成功")
    time.sleep(2)


def main():
    # 初始化浏览器实例
    browser = Chromium(9333)

    while True:
        os.system('cls')
        print((_name + ' v' + _version).center(40, '-'))
        for item in menu:
            print(item)
        print(("作者:" + _author).center(40, '-'))

        try:
            input_menu = ord(msvcrt.getch())
            if input_menu == 48:
                break
            elif input_menu == 49:
                os.system('cls')
                try:
                    dp = browser.get_tab(title='测验')
                except RuntimeError:
                    print('没有找到测验标签页。是否没有打开测验标签页?\n按任意键继续...')
                    msvcrt.getch()
                    continue
                ac = Actions(dp)
                print('请确保浏览器打开的标签页为做题页面,然后按下 Enter 继续...')
                while True:
                    key = ord(msvcrt.getch())
                    if key == 13:
                        break

                # 获取测验 URL
                url = dp.url

                # 解析 URL 中的数字
                try:
                    a = re.findall(r'\d+', url)
                except TypeError:
                    print('Url 错误, 可能是你没有打开做题页面\n按任意键继续...')
                    msvcrt.getch()
                    continue

                # 构建 API 请求URL - 修改为 DGUT LMS 的 API 地址
                try:
                    # 从URL中提取 ocId 和 homeworkId
                    ocId = None
                    homeworkId = None
                    for i, num in enumerate(a):
                        if i == 0:
                            ocId = num
                        elif i == 1:
                            homeworkId = num
                    
                    if not ocId or not homeworkId:
                        raise ValueError("无法从URL中提取必要参数")
                    
                    xhr_url = f'https://lms.dgut.edu.cn/homeworkapi/quiz/homework/stu/questions?homeworkId={homeworkId}&ocId={ocId}&showAnswer=true'
                except (IndexError, TypeError, ValueError):
                    print('Url 错误, 可能是你没有打开做题页面\n按任意键继续...')
                    msvcrt.getch()
                    continue

                # 获取 Authorization
                cookies = dp.cookies(all_domains=False)
                authorization = None
                for cookie in cookies:
                    if cookie.get('name') == 'token':
                        authorization = cookie.get('value')
                        break

                xhr_headers = {
                    'authorization': authorization,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
                }

                # 请求 API 获取答案
                try:
                    print(f'\n正在请求API...')
                    print(f'请求URL: {xhr_url}')
                    print(f'Token: {authorization[:20]}...' if authorization else 'Token: None')
                    
                    xhr_response = requests.get(url=xhr_url, headers=xhr_headers)
                    print(f'响应状态码: {xhr_response.status_code}')
                    
                    # 打印响应内容用于调试
                    print(f'响应内容: {xhr_response.text[:500]}...')
                    
                    xhr_json = xhr_response.json()
                    
                    # 验证 JSON 结构
                    if 'result' not in xhr_json:
                        print(f'\n完整响应JSON: {json.dumps(xhr_json, ensure_ascii=False, indent=2)}')
                        raise KeyError('result')
                except KeyError:
                    print('\n读取 json 键值对错误')
                    print('API返回的数据结构可能不正确')
                    print('请检查以上输出的响应内容\n按任意键继续...')
                    msvcrt.getch()
                    continue
                except requests.exceptions.JSONDecodeError:
                    print(f'\nAPI返回的不是有效的JSON格式')
                    print(f'原始响应: {xhr_response.text}')
                    print('按任意键继续...')
                    msvcrt.getch()
                    continue
                except Exception as why:
                    print(f'\n请求失败: {str(why)}')
                    print(f'错误类型: {type(why).__name__}')
                    print('按任意键继续...')
                    msvcrt.getch()
                    continue

                # 解析答案
                correct_answer = {}
                for idx, result in enumerate(xhr_json['result']):
                    correct_answer[idx] = result.get('correctAnswer', [])

                # 自动答题逻辑
                for idx in correct_answer:
                    answers = correct_answer[idx]
                    if not answers:
                        continue

                    # 处理单选题
                    if len(answers) == 1 and answers[0] in ('A', 'B', 'C', 'D', 'E'):
                        answer_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
                        answer_idx = answer_map.get(answers[0], 0)
                        if answer_idx:
                            try:
                                xpath = f'xpath://*[@id="app"]/div/div[1]/div[2]/div/div[1]/div/div/ul/li[{idx + 1}]/div[2]/ul/li[{answer_idx}]/div/label/span[1]/input'
                                element = dp.ele(xpath)
                                dp.run_js('arguments[0].click()', element)
                            except ElementNotFoundError:
                                print(f'未找到单选题元素 (第{idx + 1}题),可能是页面结构变化')
                                continue

                    # 处理多选题
                    elif len(answers) > 1 and all(a in ('A', 'B', 'C', 'D', 'E') for a in answers):
                        answer_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
                        for ans in answers:
                            answer_idx = answer_map.get(ans, 0)
                            if answer_idx:
                                try:
                                    xpath = f'xpath://*[@id="app"]/div/div[1]/div[2]/div/div[1]/div/div/ul/li[{idx + 1}]/div[2]/ul/li[{answer_idx}]/div/label/span[1]/input'
                                    element = dp.ele(xpath)
                                    dp.run_js('arguments[0].click()', element)
                                except ElementNotFoundError:
                                    print(f'未找到多选题元素 (第{idx + 1}题),可能是页面结构变化')
                                    continue

                    # 处理判断题
                    elif len(answers) == 1 and answers[0] in ('true', 'false'):
                        answer_idx = 1 if answers[0] == 'true' else 2
                        try:
                            xpath = f'xpath://*[@id="app"]/div/div[1]/div[2]/div/div[1]/div/div/ul/li[{idx + 1}]/div[2]/div[2]/label[{answer_idx}]/span[1]/input'
                            element = dp.ele(xpath)
                            dp.run_js('arguments[0].click()', element)
                        except ElementNotFoundError:
                            print(f'未找到判断题元素 (第{idx + 1}题),可能是页面结构变化')
                            continue

                    # 处理填空题
                    else:
                        try:
                            xpath = f'xpath://*[@id="app"]/div/div[1]/div[2]/div/div[1]/div/div/ul/li[{idx + 1}]/div[2]/div[2]/div[1]/div[1]/textarea'
                            element = dp.ele(xpath)
                            ac.click(element)
                            answer = ''
                            for i, a in enumerate(answers):
                                answer += a + ('\n' if i != len(answers) - 1 else '')
                            ac.key_down('CTRL').key_down('a').key_up('CTRL').type(answer).type('\n')
                        except ElementNotFoundError:
                            print(f'未找到填空题元素 (第{idx + 1}题),可能是页面结构变化')
                            continue

                print('自动答题完成!按任意键继续')
                msvcrt.getch()
                continue

            elif input_menu == 50:
                # 打开反馈页面
                browser.new_tab('https://github.com/Black-Cyan/Ulearning/issues')
                continue

            else:
                continue

        except KeyboardInterrupt:
            print('用户退出')
            exit()


if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='DGUT LMS自动答题脚本')
    parser.add_argument('-b', '--browser', help='浏览器可执行文件路径')
    args = parser.parse_args()

    # 如果提供了浏览器路径参数,则设置浏览器
    if args.browser:
        set_browser(args.browser)

    # 启动主程序
    check_config()
    try:
        check_browser()
    except FileNotFoundError as e:
        print(e)
        print("请正确配置浏览器路径,方法如下:")
        print(f"1. 运行脚本时添加参数: -b 浏览器可执行文件完整路径 或者编辑配置文件 {config_file}")
        print("2. 示例: .\\DGUT_LMS.exe -b \"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe\"")
        print("3. 可在浏览器地址栏输入 'edge://version' 或 'chrome://version' 查看安装路径")
        exit()

    main()