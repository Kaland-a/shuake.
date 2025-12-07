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

current_file = os.path.abspath(sys.executable)  # 如果没有打包直接运行，则参数应改为 __file__
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

        print(f'配置文件不存在，已为您创建配置文件: {config_file}')


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
        print(("作者：" + _author).center(40, '-'))

        try:
            input_menu = ord(msvcrt.getch())
            if input_menu == 48:
                break
            elif input_menu == 49:
                os.system('cls')
                try:
                    dp = browser.get_tab(title='测验')
                except RuntimeError:
                    print('没有找到测验标签页。是否没有打开测验标签页？\n按任意键继续...')
                    msvcrt.getch()
                    continue
                ac = Actions(dp)
                print('请确保浏览器打开的标签页为做题页面，然后按下 Enter 继续...')
                while True:
                    key = ord(msvcrt.getch())
                    if key == 13:
                        break

                # 获取测验 URL
                url = dp.url

                # 解析 URL 中的数字
                try:
                    a = re.findall('\d+', url)
                except TypeError:
                    print('Url 错误, 可能是你没有打开做题页面\n按任意键继续...')
                    msvcrt.getch()
                    continue

                # 构建 API 请求URL - DGUT使用不同的域名
                try:
                    xhr_url = f'https://lms.dgut.edu.cn/homeworkapi/quiz/homework/stu/questions?homeworkId={a[1]}&ocId={a[0]}&showAnswer=true'
                except (IndexError, TypeError):
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
                    xhr_response = requests.get(url=xhr_url, headers=xhr_headers)
                    xhr_json = xhr_response.json()
                    # 验证 JSON 结构
                    if 'result' not in xhr_json:
                        raise KeyError('result')
                except KeyError:
                    print('读取 json 键值对错误\n可能是你粘贴了错误的 Url 或 Authorization ?\n按任意键继续...')
                    msvcrt.getch()
                    continue
                except Exception as why:
                    print(f'请求失败: {str(why)}\n按任意键继续...')
                    msvcrt.getch()
                    continue

                # 解析答案
                correct_answer = {}
                for idx, result in enumerate(xhr_json['result']):
                    correct_answer[idx] = result.get('correctAnswer', [])

                print(f'成功获取 {len(correct_answer)} 道题目的答案，开始自动答题...\n')

                # 自动答题逻辑 - 根据DGUT的页面结构修改
                for idx in correct_answer:
                    answers = correct_answer[idx]
                    if not answers:
                        print(f'第 {idx + 1} 题没有答案，跳过')
                        continue

                    try:
                        # 处理单选题和多选题 - 使用class选择器定位选项
                        if all(a in ('A', 'B', 'C', 'D', 'E', 'F', 'G') for a in answers):
                            answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6}
                            
                            # 尝试找到题目容器
                            question_containers = dp.eles('css:.question-item')
                            if idx < len(question_containers):
                                question_container = question_containers[idx]
                                
                                # 在题目容器内查找选项
                                choice_elements = question_container.eles('css:.choice-title')
                                
                                for ans in answers:
                                    answer_idx = answer_map.get(ans)
                                    if answer_idx is not None and answer_idx < len(choice_elements):
                                        try:
                                            # 点击选项标题所在的div
                                            choice_element = choice_elements[answer_idx]
                                            dp.run_js('arguments[0].click()', choice_element)
                                            print(f'第 {idx + 1} 题选择了选项 {ans}')
                                            time.sleep(0.1)
                                        except Exception as e:
                                            print(f'第 {idx + 1} 题点击选项 {ans} 失败: {e}')
                                            continue

                        # 处理判断题
                        elif len(answers) == 1 and answers[0] in ('true', 'false'):
                            question_containers = dp.eles('css:.question-item')
                            if idx < len(question_containers):
                                question_container = question_containers[idx]
                                
                                # 查找判断题的radio输入框
                                radio_inputs = question_container.eles('css:input[type="radio"]')
                                
                                # 遍历找到value匹配的radio按钮
                                for radio in radio_inputs:
                                    try:
                                        radio_value = radio.attr('value')
                                        if radio_value == answers[0]:
                                            # 点击对应的radio输入框
                                            dp.run_js('arguments[0].click()', radio)
                                            print(f'第 {idx + 1} 题选择了 {"正确" if answers[0] == "true" else "错误"}')
                                            break
                                    except Exception as e:
                                        print(f'第 {idx + 1} 题点击判断选项失败: {e}')
                                        continue

                        # 处理填空题
                        else:
                            question_containers = dp.eles('css:.question-item')
                            if idx < len(question_containers):
                                question_container = question_containers[idx]
                                
                                # 查找填空输入框
                                blank_inputs = question_container.eles('css:.blank-item-input')
                                
                                # 如果答案数量和输入框数量匹配
                                for i, answer in enumerate(answers):
                                    if i < len(blank_inputs):
                                        try:
                                            input_element = blank_inputs[i]
                                            ac.click(input_element)
                                            # 清空并输入答案
                                            ac.key_down('CTRL').key_down('a').key_up('CTRL').type(answer)
                                            print(f'第 {idx + 1} 题第 {i + 1} 个空填入: {answer}')
                                            time.sleep(0.1)
                                        except Exception as e:
                                            print(f'第 {idx + 1} 题填空失败: {e}')
                                            continue

                    except ElementNotFoundError:
                        print(f'第 {idx + 1} 题元素未找到，可能是页面结构变化')
                        continue
                    except Exception as e:
                        print(f'第 {idx + 1} 题处理出错: {e}')
                        continue

                print('\n自动答题完成！按任意键继续')
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

    # 如果提供了浏览器路径参数，则设置浏览器
    if args.browser:
        set_browser(args.browser)

    # 启动主程序
    check_config()
    try:
        check_browser()
    except FileNotFoundError as e:
        print(e)
        print("请正确配置浏览器路径，方法如下：")
        print(f"1. 运行脚本时添加参数: -b 浏览器可执行文件完整路径 或者编辑配置文件 {config_file}")
        print("2. 示例: .\\DGUT_LMS.exe -b \"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe\"")
        print("3. 可在浏览器地址栏输入 'edge://version' 或 'chrome://version' 查看安装路径")
        exit()

    main()
