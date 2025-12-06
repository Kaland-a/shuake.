import requests
import json
import os
import hashlib
import smtplib
import email
from apscheduler.schedulers.background import BackgroundScheduler
import time
from datetime import datetime
import configparser
import sys
import re

class UlearningDGUT:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.headers = {}
        self.Token = None
        self.config = None
        self.is_running = False
        self.session = requests.Session()
        
        self.log("=" * 50)
        self.log("优学院自动签到助手 - 东莞理工学院版")
        self.log("=" * 50)
        
        self.load_config()
    
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        try:
            with open('app.log', 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except:
            pass
    
    def load_config(self):
        try:
            if not os.path.exists('config.ini'):
                self.log("未找到配置文件,开始创建...")
                self.create_config()
                return
            
            self.config = configparser.ConfigParser()
            self.config.read('config.ini', encoding='utf-8')
            
            required = {
                'Account': ['username', 'password'],
                'Location': ['lat', 'lon']
            }
            
            missing = []
            for section, keys in required.items():
                if section not in self.config:
                    missing.append(f"[{section}]")
                else:
                    for key in keys:
                        if not self.config[section].get(key):
                            missing.append(f"{section}.{key}")
            
            if missing:
                self.log(f"配置不完整,缺少: {', '.join(missing)}")
                if self.confirm("是否现在配置?"):
                    self.create_config()
            else:
                self.log("✓ 配置加载成功")
                
                if os.path.exists('cookie.txt'):
                    try:
                        with open('cookie.txt', 'r', encoding='utf-8') as f:
                            saved_token = json.loads(f.read())
                            if 'token' in saved_token:
                                self.Token = saved_token
                                token = saved_token['token']
                                
                                self.headers = {
                                    'token': token,
                                    'Authorization': token,
                                    'Cookie': f'token={token}',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Content-Type': 'application/json;charset=UTF-8'
                                }
                                
                                # 设置 session cookies
                                domains = ['.dgut.edu.cn', 'lms.dgut.edu.cn', 'dgut.ulearning.cn', 'courseapi.ulearning.cn']
                                for domain in domains:
                                    self.session.cookies.set('token', token, domain=domain)
                                
                                self.log(f"✓ 已加载token: {token[:8]}...{token[-8:]}")
                    except Exception as e:
                        self.log(f"加载token失败: {str(e)}")
                
        except Exception as e:
            self.log(f"✗ 加载配置失败: {str(e)}")
            self.create_config()
    
    def create_config(self):
        print("\n" + "=" * 50)
        print("配置向导 - 东莞理工学院")
        print("=" * 50)
        
        config = configparser.ConfigParser()
        
        print("\n【账号配置】")
        print("格式: dgut+学号,例如 dgut2023463030604")
        username = input("账号: ").strip()
        
        if username.isdigit():
            username = "dgut" + username
            print(f"已添加前缀: {username}")
        
        password = input("密码: ").strip()
        
        config['Account'] = {
            'username': username,
            'password': password
        }
        
        print("\n【地理位置】")
        print("松山湖校区默认: 纬度 22.927, 经度 113.881")
        lat = input("纬度 [回车用默认]: ").strip() or "22.927"
        lon = input("经度 [回车用默认]: ").strip() or "113.881"
        
        config['Location'] = {
            'lat': lat,
            'lon': lon
        }
        
        print("\n【邮件配置(可选)】")
        from_addr = input("发件邮箱: ").strip() or ""
        auth_code = input("授权码: ").strip() or ""
        to_addr = input("收件邮箱: ").strip() or ""
        
        config['Email'] = {
            'from_addr': from_addr,
            'auth_code': auth_code,
            'to_addr': to_addr
        }
        
        try:
            with open('config.ini', 'w', encoding='utf-8') as f:
                config.write(f)
            self.log("✓ 配置已保存")
            self.config = config
        except Exception as e:
            self.log(f"✗ 保存失败: {str(e)}")
            sys.exit(1)
    
    def confirm(self, message):
        response = input(f"{message} (y/n): ").strip().lower()
        return response in ['y', 'yes', '是']
    
    def login(self):
        self.log("开始登录 - 东莞理工学院应用平台")
        
        username = self.config['Account']['username']
        password = self.config['Account']['password']
        
        # 方案1: 尝试使用 Selenium 自动登录
        self.log("\n尝试自动登录...")
        if self.login_with_selenium():
            return True
        
        # 方案2: 手动输入 Token
        self.log("\n" + "=" * 50)
        self.log("⚠ 自动登录失败,使用手动方案")
        self.log("=" * 50)
        self.log("\n详细步骤:")
        self.log("1. 浏览器访问: https://application.dgut.edu.cn/application/#/login")
        self.log(f"2. 输入账号: {username}")
        self.log("3. 输入密码并登录")
        self.log("4. 点击'优学院'应用图标")
        self.log("5. 进入优学院后,按F12 -> Application -> Cookies")
        self.log("6. 找到token,复制值")
        self.log("7. 程序菜单选9,粘贴token")
        self.log("=" * 50)
        
        if self.confirm("\n是否手动输入token?"):
            return self.manual_token_input()
        
        return False
    
    def login_with_selenium(self):
        """使用 Selenium 自动登录东莞理工应用平台"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            import time
            
            self.log("方案1: 使用浏览器自动化登录...")
            
            username = self.config['Account']['username']
            password = self.config['Account']['password']
            
            # 配置浏览器选项
            chrome_options = Options()
            # 注释掉无头模式以便调试，成功后可以取消注释
            # chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.log("启动浏览器...")
            
            try:
                driver = webdriver.Chrome(options=chrome_options)
                # 隐藏webdriver特征
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                })
            except:
                try:
                    from selenium.webdriver.edge.options import Options as EdgeOptions
                    edge_options = EdgeOptions()
                    edge_options.add_argument('--no-sandbox')
                    edge_options.add_argument('--disable-dev-shm-usage')
                    driver = webdriver.Edge(options=edge_options)
                except:
                    self.log("✗ 未找到浏览器驱动")
                    self.log("提示: 请安装 ChromeDriver 或 EdgeDriver")
                    return False
            
            try:
                # 步骤1: 访问应用平台登录页
                login_url = "https://application.dgut.edu.cn/application/#/login"
                self.log(f"步骤1: 访问应用平台登录页")
                driver.get(login_url)
                
                wait = WebDriverWait(driver, 20)
                time.sleep(2)
                
                # 步骤2: 检查是否有"账号登录"标签页，如果有则点击
                self.log("步骤2: 查找登录表单...")
                try:
                    # 尝试点击"账号登录"标签
                    account_login_tab = driver.find_element(By.XPATH, "//*[contains(text(), '账号登录')]")
                    account_login_tab.click()
                    self.log("✓ 切换到账号登录")
                    time.sleep(1)
                except:
                    self.log("默认为账号登录模式")
                
                # 步骤3: 输入用户名
                self.log("步骤3: 输入账号信息...")
                
                # 查找用户名输入框
                username_selectors = [
                    "//input[@placeholder='dgut2023463030604']",
                    "//input[@placeholder='用户名']",
                    "//input[@name='username']",
                    "//input[@type='text']",
                    "//input[contains(@placeholder, 'dgut')]",
                    "//input[contains(@placeholder, '用户')]"
                ]
                
                username_input = None
                for selector in username_selectors:
                    try:
                        username_input = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                        if username_input.is_displayed():
                            break
                    except:
                        continue
                
                if not username_input:
                    self.log("✗ 未找到用户名输入框")
                    driver.save_screenshot('login_page.png')
                    self.log("已保存截图到 login_page.png")
                    driver.quit()
                    return False
                
                username_input.clear()
                time.sleep(0.5)
                username_input.send_keys(username)
                self.log(f"✓ 输入用户名: {username}")
                time.sleep(0.5)
                
                # 步骤4: 输入密码
                password_selectors = [
                    "//input[@placeholder='密码']",
                    "//input[@name='password']",
                    "//input[@type='password']"
                ]
                
                password_input = None
                for selector in password_selectors:
                    try:
                        password_input = driver.find_element(By.XPATH, selector)
                        if password_input.is_displayed():
                            break
                    except:
                        continue
                
                if not password_input:
                    self.log("✗ 未找到密码输入框")
                    driver.quit()
                    return False
                
                password_input.clear()
                time.sleep(0.5)
                password_input.send_keys(password)
                self.log("✓ 输入密码")
                time.sleep(0.5)
                
                # 步骤5: 点击登录按钮
                self.log("步骤5: 点击登录按钮...")
                
                login_button_selectors = [
                    "//button[contains(text(), '登录')]",
                    "//button[contains(text(), '登')]",
                    "//button[@type='submit']",
                    "//input[@type='submit']",
                    "//button[contains(@class, 'login')]",
                    "//*[@role='button' and contains(text(), '登')]"
                ]
                
                login_button = None
                for selector in login_button_selectors:
                    try:
                        login_button = driver.find_element(By.XPATH, selector)
                        if login_button.is_displayed() and login_button.is_enabled():
                            break
                    except:
                        continue
                
                if not login_button:
                    self.log("✗ 未找到登录按钮")
                    driver.save_screenshot('no_login_button.png')
                    driver.quit()
                    return False
                
                try:
                    login_button.click()
                    self.log("✓ 点击登录按钮")
                except:
                    driver.execute_script("arguments[0].click();", login_button)
                    self.log("✓ 点击登录按钮 (JavaScript)")
                
                # 步骤6: 等待登录完成,检查是否跳转
                time.sleep(3)
                current_url = driver.current_url
                self.log(f"登录后URL: {current_url}")
                
                # 检查是否登录成功
                if 'error' in current_url.lower() or driver.find_elements(By.XPATH, "//*[contains(text(), '错误')]"):
                    self.log("✗ 登录失败,请检查账号密码")
                    driver.save_screenshot('login_failed.png')
                    driver.quit()
                    return False
                
                # 步骤7: 查找并点击"优学院"应用
                self.log("步骤7: 查找'优学院'应用...")
                time.sleep(2)
                
                # 多种方式查找优学院
                ulearning_selectors = [
                    "//div[contains(text(), '优学院')]",
                    "//span[contains(text(), '优学院')]",
                    "//*[contains(text(), '优学院')]",
                    "//a[contains(@href, 'ulearning')]",
                    "//img[contains(@alt, '优学院')]/..",
                    "//div[contains(@class, 'app')]//div[contains(text(), '优')]"
                ]
                
                ulearning_found = False
                for selector in ulearning_selectors:
                    try:
                        ulearning_app = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        self.log(f"✓ 找到'优学院'应用: {selector}")
                        
                        # 滚动到元素可见
                        driver.execute_script("arguments[0].scrollIntoView(true);", ulearning_app)
                        time.sleep(1)
                        
                        ulearning_app.click()
                        self.log("✓ 点击'优学院'应用")
                        ulearning_found = True
                        time.sleep(3)
                        break
                    except:
                        continue
                
                if not ulearning_found:
                    self.log("⚠ 未找到'优学院'应用图标")
                    self.log("尝试直接访问新版LMS系统...")
                    # 直接访问新版LMS系统
                    driver.get("https://lms.dgut.edu.cn/courseweb/ulearning/index.html")
                    time.sleep(3)
                
                # 步骤8: 切换到优学院窗口并获取Token
                self.log("步骤8: 获取Token...")
                
                # 如果打开了新标签页,切换到最新的窗口
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(2)
                
                current_url = driver.current_url
                self.log(f"当前URL: {current_url}")
                
                # 获取所有cookies
                cookies = driver.get_cookies()
                self.log(f"获取到 {len(cookies)} 个cookies")
                
                # 查找token
                token = None
                for cookie in cookies:
                    self.log(f"Cookie: {cookie['name']} = {cookie['value'][:20]}...")
                    if cookie['name'].lower() == 'token':
                        token = cookie['value']
                        self.log(f"✓ 从Cookies找到token: {token[:8]}...{token[-8:]}")
                        break
                
                # 尝试从localStorage获取
                if not token:
                    try:
                        token = driver.execute_script("return localStorage.getItem('token')")
                        if token:
                            self.log(f"✓ 从localStorage获取token: {token[:8]}...{token[-8:]}")
                    except:
                        pass
                
                # 尝试从sessionStorage获取
                if not token:
                    try:
                        token = driver.execute_script("return sessionStorage.getItem('token')")
                        if token:
                            self.log(f"✓ 从sessionStorage获取token: {token[:8]}...{token[-8:]}")
                    except:
                        pass
                
                # 尝试所有可能的key
                if not token:
                    storage_keys = ['token', 'access_token', 'accessToken', 'TOKEN', 'auth_token', 'userToken']
                    for key in storage_keys:
                        try:
                            val = driver.execute_script(f"return localStorage.getItem('{key}')")
                            if val:
                                token = val
                                self.log(f"✓ 从localStorage[{key}]获取token")
                                break
                            val = driver.execute_script(f"return sessionStorage.getItem('{key}')")
                            if val:
                                token = val
                                self.log(f"✓ 从sessionStorage[{key}]获取token")
                                break
                        except:
                            pass
                
                # 保存截图
                try:
                    driver.save_screenshot('ulearning_page.png')
                    self.log("✓ 已保存页面截图到 ulearning_page.png")
                except:
                    pass
                
                # 保存页面HTML用于调试
                try:
                    with open('ulearning_page.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    self.log("✓ 已保存页面HTML到 ulearning_page.html")
                except:
                    pass
                
                driver.quit()
                
                if token:
                    return self.save_token(token, {'token': token, 'userID': 'auto'})
                else:
                    self.log("✗ 未能获取token")
                    self.log("提示: 请检查 ulearning_page.png 和 ulearning_page.html")
                    return False
                    
            except Exception as e:
                self.log(f"✗ 浏览器操作失败: {str(e)}")
                import traceback
                self.log(traceback.format_exc())
                try:
                    driver.save_screenshot('error_page.png')
                    self.log("已保存错误截图到 error_page.png")
                except:
                    pass
                try:
                    driver.quit()
                except:
                    pass
                return False
                
        except ImportError:
            self.log("✗ 未安装 selenium")
            self.log("提示: pip install selenium")
            return False
        except Exception as e:
            self.log(f"✗ Selenium 初始化失败: {str(e)}")
            return False
    
    def save_token(self, token, full_data):
        try:
            self.Token = full_data
            self.Token['token'] = token
            
            # 设置headers (现在使用普通token,不是VNK)
            self.headers = {
                'token': token,
                'Authorization': token,
                'Cookie': f'token={token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/json;charset=UTF-8',
                'Origin': 'https://lms.dgut.edu.cn',
                'Referer': 'https://lms.dgut.edu.cn/courseweb/ulearning/index.html'
            }
            
            # 在session中设置cookie (支持多个域名)
            domains = ['.dgut.edu.cn', 'lms.dgut.edu.cn', 'dgut.ulearning.cn', 'courseapi.ulearning.cn', 'application.dgut.edu.cn']
            for domain in domains:
                self.session.cookies.set('token', token, domain=domain)
            
            # 保存到文件
            with open('cookie.txt', 'w', encoding='utf-8') as f:
                f.write(json.dumps(self.Token, ensure_ascii=False, indent=2))
            
            self.log(f"✓ 登录成功! Token: {token[:8] if len(token) > 8 else token}...")
            
            # 验证token是否有效
            if self.verify_token():
                self.log("✓ Token验证通过")
            else:
                self.log("⚠ Token未验证,但已保存")
            
            return True
        except Exception as e:
            self.log(f"保存token失败: {str(e)}")
            return False
    
    def manual_token_input(self):
        print("\n请输入token:")
        print("(从浏览器 F12 -> Application -> Cookies 中复制 token 的值)")
        token = input("Token: ").strip()
        
        if token:
            self.Token = {'token': token, 'userID': 'manual'}
            
            self.headers = {
                'token': token,
                'Authorization': token,
                'Cookie': f'token={token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/json;charset=UTF-8'
            }
            
            # 设置session cookies
            domains = ['.dgut.edu.cn', 'lms.dgut.edu.cn', 'dgut.ulearning.cn', 'courseapi.ulearning.cn']
            for domain in domains:
                self.session.cookies.set('token', token, domain=domain)
            
            with open('cookie.txt', 'w', encoding='utf-8') as f:
                f.write(json.dumps(self.Token, ensure_ascii=False, indent=2))
            
            self.log(f"✓ Token已保存: {token[:8]}...{token[-8:]}")
            
            if self.verify_token():
                self.log("✓ Token验证成功!")
                return True
            else:
                self.log("⚠ Token未验证,但已保存")
                return True
        
        return False
    
    def verify_token(self):
        try:
            courses = self.get_courses_list()
            return len(courses) > 0
        except:
            return False
    
    def get_courses_list(self):
        # 新版LMS系统API端点
        apis = [
            "https://lms.dgut.edu.cn/courseweb/api/courses/students?publishStatus=-1&pn=1&ps=20&type=1",
            "https://lms.dgut.edu.cn/api/courses/students?publishStatus=-1&pn=1&ps=20&type=1",
            "https://courseapi.ulearning.cn/courses/students?publishStatus=-1&pn=1&ps=20&type=1",
            "https://dgut.ulearning.cn/api/courses/students?publishStatus=-1&pn=1&ps=20&type=1"
        ]
        
        for api in apis:
            try:
                headers = self.headers.copy()
                if self.Token and 'token' in self.Token:
                    headers['token'] = self.Token['token']
                
                # 添加LMS系统需要的headers
                headers['Referer'] = 'https://lms.dgut.edu.cn/courseweb/ulearning/index.html'
                headers['Origin'] = 'https://lms.dgut.edu.cn'
                
                response = self.session.get(api, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    res = response.json()
                    
                    if 'courseList' in res:
                        courses = res['courseList']
                        self.log(f"✓ 获取到 {len(courses)} 门课程")
                        return courses
                    elif 'data' in res and isinstance(res['data'], dict) and 'courseList' in res['data']:
                        courses = res['data']['courseList']
                        self.log(f"✓ 获取到 {len(courses)} 门课程")
                        return courses
                    elif 'data' in res and isinstance(res['data'], list):
                        courses = res['data']
                        self.log(f"✓ 获取到 {len(courses)} 门课程")
                        return courses
            except Exception as e:
                self.log(f"API {api} 请求失败: {str(e)}")
                continue
        
        self.log("✗ 获取课程失败,Token可能过期")
        return []
    
    def check_homework(self):
        self.log("\n" + "=" * 50)
        self.log("开始检查作业...")
        
        courses_list = self.get_courses_list()
        if not courses_list:
            return
        
        unfinished = []
        
        for course in courses_list:
            course_name = course['name']
            course_id = course.get('id') or course.get('courseId')
            
            # 新版LMS系统API
            apis = [
                f"https://lms.dgut.edu.cn/courseweb/api/homeworks/student?ocId={course_id}&pn=1&ps=20",
                f"https://lms.dgut.edu.cn/api/homeworks/student?ocId={course_id}&pn=1&ps=20",
                f"https://courseapi.ulearning.cn/homeworks/student?ocId={course_id}&pn=1&ps=20",
                f"https://dgut.ulearning.cn/api/homeworks/student?ocId={course_id}&pn=1&ps=20"
            ]
            
            for api in apis:
                try:
                    headers = self.headers.copy()
                    headers['Referer'] = f'https://lms.dgut.edu.cn/courseweb/ulearning/index.html#/course/resource?courseId={course_id}'
                    headers['Origin'] = 'https://lms.dgut.edu.cn'
                    
                    response = self.session.get(api, headers=headers, timeout=10)
                    res = response.json()
                    
                    homework_list = res.get('homeworkList') or res.get('data', [])
                    
                    if homework_list:
                        for hw in homework_list:
                            if hw.get('timeStatus') == '2' and not hw.get('score') and hw.get('state') == 0:
                                hw_info = f"{course_name} - {hw.get('homeworkTitle', '未知')}"
                                unfinished.append(hw_info)
                                self.log(f"  未完成: {hw_info}")
                        break
                except:
                    continue
        
        if unfinished:
            self.log(f"\n共 {len(unfinished)} 个未完成作业")
            self.send_email("\n".join(unfinished), "作业提醒")
        else:
            self.log("✓ 无未完成作业")
    
    def auto_checkin(self, code_mode=False):
        self.log("\n" + "=" * 50)
        self.log("开始检查签到...")
        
        courses_list = self.get_courses_list()
        if not courses_list:
            return
        
        signed = []
        need_code = []
        
        for course in courses_list:
            course_name = course['name']
            course_id = course.get('id') or course.get('courseId')
            
            # 新版LMS系统API
            apis = [
                f"https://lms.dgut.edu.cn/courseweb/api/classActivity/stu/{course_id}/-1?pn=1&ps=20",
                f"https://lms.dgut.edu.cn/api/classActivity/stu/{course_id}/-1?pn=1&ps=20",
                f"https://courseapi.ulearning.cn/classActivity/stu/{course_id}/-1?pn=1&ps=20",
                f"https://dgut.ulearning.cn/api/classActivity/stu/{course_id}/-1?pn=1&ps=20"
            ]
            
            for api in apis:
                try:
                    headers = self.headers.copy()
                    headers['Referer'] = f'https://lms.dgut.edu.cn/courseweb/ulearning/index.html#/course/resource?courseId={course_id}'
                    headers['Origin'] = 'https://lms.dgut.edu.cn'
                    
                    response = self.session.get(api, headers=headers, timeout=10)
                    res = response.json()
                    
                    activity_list = res.get('list') or res.get('data', [])
                    
                    if activity_list:
                        for activity in activity_list:
                            if activity.get('timeStatus') == 2 and activity.get('status') != 1:
                                attend_type = activity.get('type', 0)
                                class_id = course.get('classId')
                                
                                if attend_type == 1:
                                    self.log(f"  ⚠ {course_name} 需要签到码")
                                    need_code.append(course_name)
                                    
                                    if code_mode:
                                        code = input(f"    请输入签到码: ").strip()
                                        if self.post_attend(activity, class_id, code):
                                            signed.append(course_name)
                                            self.log(f"  ✓ {course_name} 签到成功")
                                    else:
                                        code = self.get_preset_code(course_name)
                                        if code and self.post_attend(activity, class_id, code):
                                            signed.append(course_name)
                                            self.log(f"  ✓ {course_name} 签到成功(预设)")
                                else:
                                    if self.post_attend(activity, class_id):
                                        signed.append(course_name)
                                        self.log(f"  ✓ {course_name} 签到成功")
                        break
                except:
                    continue
        
        if signed:
            self.send_email(f"已签到: {', '.join(signed)}", "签到通知")
            self.log(f"\n共 {len(signed)} 个签到")
        
        if need_code and not code_mode:
            self.log(f"\n{len(need_code)} 个需签到码,用菜单3")
        
        if not signed and not need_code:
            self.log("✓ 无需签到")
    
    def post_attend(self, activity, class_id, code=""):
        lat = self.config['Location']['lat']
        lon = self.config['Location']['lon']
        
        user_id = self.Token.get('userID') or self.Token.get('userId', 'unknown')
        
        payload = {
            "attendanceID": activity['relationId'],
            "classID": class_id,
            "userID": user_id,
            "location": f"{lon},{lat}",
            "enterWay": 1,
            "attendanceCode": code
        }
        
        # 新版LMS系统API
        apis = [
            "https://lms.dgut.edu.cn/courseweb/api/newAttendance/signByStu",
            "https://lms.dgut.edu.cn/api/newAttendance/signByStu",
            "https://courseapi.ulearning.cn/newAttendance/signByStu",
            "https://apps.ulearning.cn/newAttendance/signByStu"
        ]
        
        for api in apis:
            try:
                headers = self.headers.copy()
                headers['Referer'] = 'https://lms.dgut.edu.cn/courseweb/ulearning/index.html'
                headers['Origin'] = 'https://lms.dgut.edu.cn'
                
                response = self.session.post(
                    api,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=10
                )
                res = response.json()
                
                if res.get('status') == 200 or res.get('code') == 0:
                    return True
            except:
                continue
        
        return False
    
    def get_preset_code(self, course_name):
        if 'SignCodes' in self.config:
            return self.config['SignCodes'].get(course_name)
        return None
    
    def manage_sign_codes(self):
        if 'SignCodes' not in self.config:
            self.config.add_section('SignCodes')
        
        while True:
            print("\n" + "=" * 50)
            print("签到码管理")
            print("=" * 50)
            
            if len(self.config['SignCodes']) == 0:
                print("  (无)")
            else:
                for course, code in self.config['SignCodes'].items():
                    print(f"  {course}: {code}")
            
            print("\n1. 添加/修改")
            print("2. 删除")
            print("0. 返回")
            
            choice = input("\n选择: ").strip()
            
            if choice == '1':
                course = input("课程名: ").strip()
                code = input("签到码: ").strip()
                self.config['SignCodes'][course] = code
                self.save_config()
                self.log("✓ 已保存")
            elif choice == '2':
                course = input("课程名: ").strip()
                if course in self.config['SignCodes']:
                    del self.config['SignCodes'][course]
                    self.save_config()
                    self.log("✓ 已删除")
            elif choice == '0':
                break
    
    def save_config(self):
        try:
            with open('config.ini', 'w', encoding='utf-8') as f:
                self.config.write(f)
        except:
            pass
    
    def send_email(self, content, subject):
        if not self.config['Email'].get('from_addr'):
            return
        
        try:
            conn = smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=10)
            conn.login(
                self.config['Email']['from_addr'],
                self.config['Email']['auth_code']
            )
            
            msg = email.message.EmailMessage()
            msg.set_content(content)
            msg['subject'] = subject
            msg['from'] = self.config['Email']['from_addr']
            msg['to'] = self.config['Email']['to_addr']
            
            conn.send_message(msg)
            conn.close()
            self.log("✓ 邮件已发送")
        except:
            pass
    
    def start_service(self):
        if not self.Token:
            self.log("未登录,请先登录")
            if self.confirm("手动输入token?"):
                if not self.manual_token_input():
                    return False
            elif not self.login():
                return False
        
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.scheduler = BackgroundScheduler()
        
        self.scheduler.add_job(
            self.check_homework,
            'cron',
            hour=8,
            minute=0,
            id='homework',
            misfire_grace_time=300
        )
        self.scheduler.add_job(
            lambda: self.auto_checkin(code_mode=False),
            'interval',
            minutes=2,
            id='checkin',
            misfire_grace_time=60
        )
        
        self.scheduler.start()
        self.is_running = True
        
        self.log("\n✓ 服务已启动")
        self.log("  每天8:00检查作业")
        self.log("  每2分钟检查签到")
        
        return True
    
    def stop_service(self):
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            self.is_running = False
            self.log("✓ 服务已停止")
        except:
            self.is_running = False
    
    def show_menu(self):
        while True:
            print("\n" + "=" * 50)
            print("主菜单 - 东莞理工学院")
            print("=" * 50)
            print("1. 启动自动服务")
            print("2. 手动签到")
            print("3. 签到(需要码)")
            print("4. 检查作业")
            print("5. 测试登录")
            print("6. 管理签到码")
            print("7. 重新配置")
            print("8. 查看配置")
            print("9. 手动输入Token (推荐)")
            print("0. 退出")
            print("=" * 50)
            
            choice = input("选择: ").strip()
            
            if choice == '1':
                if self.is_running:
                    if self.confirm("停止服务?"):
                        self.stop_service()
                    else:
                        continue
                self.start_service()
            
            elif choice == '2':
                if not self.Token:
                    if self.confirm("未登录,手动输入token?"):
                        if not self.manual_token_input():
                            continue
                    elif not self.login():
                        continue
                self.auto_checkin(code_mode=False)
            
            elif choice == '3':
                if not self.Token:
                    if self.confirm("未登录,手动输入token?"):
                        if not self.manual_token_input():
                            continue
                    elif not self.login():
                        continue
                self.auto_checkin(code_mode=True)
            
            elif choice == '4':
                if not self.Token:
                    if self.confirm("未登录,手动输入token?"):
                        if not self.manual_token_input():
                            continue
                    elif not self.login():
                        continue
                self.check_homework()
            
            elif choice == '5':
                self.login()
            
            elif choice == '6':
                self.manage_sign_codes()
            
            elif choice == '7':
                self.create_config()
            
            elif choice == '8':
                self.show_config()
            
            elif choice == '9':
                self.manual_token_input()
            
            elif choice == '0':
                if self.is_running:
                    self.stop_service()
                self.log("再见!")
                break
    
    def show_config(self):
        print("\n" + "=" * 50)
        print("当前配置")
        print("=" * 50)
        
        if not self.config:
            print("未加载配置")
            return
        
        print(f"\n账号: {self.config['Account'].get('username')}")
        print(f"密码: {'*' * 8}")
        print(f"位置: {self.config['Location'].get('lat')}, {self.config['Location'].get('lon')}")
        
        if self.Token and 'token' in self.Token:
            token = self.Token['token']
            print(f"\nToken: {token[:8]}...{token[-8:] if len(token) > 8 else ''}")

def main():
    app = None
    try:
        app = UlearningDGUT()
        app.show_menu()
    except KeyboardInterrupt:
        print("\n\n程序中断")
        if app and app.is_running:
            app.stop_service()
    except Exception as e:
        import traceback
        print(f"\n错误: {str(e)}")
        print(traceback.format_exc())
        input("\n按回车退出...")
    finally:
        if app and app.scheduler.running:
            try:
                app.scheduler.shutdown(wait=False)
            except:
                pass

if __name__ == '__main__':
    main()