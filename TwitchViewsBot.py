"""
    *******************************************************************************************
    TwitchViewsBot: A Multi-Threaded Twitch Views Bot with Built-in Proxy Manager
    Author: Ali Toori, Python Developer [Bot Builder]
    Website: https://boteaz.com
    YouTube: https://youtube.com/@AliToori
    *******************************************************************************************
"""
import json
import os
import random
import subprocess
import zipfile
from pathlib import Path
import ntplib
import time
from time import sleep
import datetime
from datetime import datetime
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
import psutil
import pyfiglet
import toml
import sys
import requests
import logging.config
from multiprocessing import freeze_support
from tkinter.scrolledtext import ScrolledText
from playwright.sync_api import sync_playwright
from selenium import webdriver
from concurrent.futures.thread import ThreadPoolExecutor
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from streamlink import Streamlink


def get_logger():
    """
    Get logger file handler
    :return: LOGGER
    """
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        'formatters': {
            'colored': {
                '()': 'colorlog.ColoredFormatter',  # colored output
                # --> %(log_color)s is very important, that's what colors the line
                'format': '[%(asctime)s,%(lineno)s] %(log_color)s[%(message)s]',
                'log_colors': {
                    'DEBUG': 'green',
                    'INFO': 'cyan',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'bold_red',
                },
            },
            'simple': {
                'format': '[%(asctime)s,%(lineno)s] [%(message)s]',
            },
        },
        "handlers": {
            "console": {
                "class": "colorlog.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "simple",
                "filename": "TwitchViewsBot.log",
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 1
            },
        },
        "root": {"level": "INFO",
                 "handlers": ["console", "file"]
                 }
    })
    return logging.getLogger()


LOGGER = get_logger()


# Browser Instance
class Instance:
    def __init__(self, user_agent, target_url, proxy, location_info, headless, instance_id=-1):
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.driver = None
        self.actions = None
        self.playwright = None
        self.context = None
        self.browser = None
        self.page = None
        self.last_active_resume_time = 0
        self.last_active_timestamp = None
        self.is_watching = False
        self.id = instance_id
        self.user_agent = user_agent
        self.proxy = proxy
        self.target_url = target_url
        self._headless = headless
        self.fully_initialized = False
        self.command = None
        self.location_info = location_info
        if not self.location_info:
            self.location_info = {
                'index': -1,
                'x': 0,
                'y': 0,
                'width': 500,
                'height': 300,
                'free': True}
    
    # Loads web driver with configurations
    def get_driver(self, proxy=False, headless=False):
        driver_bin = str(self.PROJECT_ROOT / "BotRes/bin/chromedriver.exe")
        service = Service(executable_path=driver_bin)
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        prefs = {"directory_upgrade": True,
                 "credentials_enable_service": False,
                 "profile.password_manager_enabled": False,
                 "profile.default_content_settings.popups": False,
                 # "profile.managed_default_content_settings.images": 2,
                 f"download.default_directory": f"{self.directory_downloads}",
                 "profile.default_content_setting_values.geolocation": 2
                 }
        options.add_experimental_option("prefs", prefs)
        options.add_argument(F'--user-agent={random.choice(self.user_agents)}')
        # Set a proxy based on type i.e. Authenticated or simple
        if proxy:
            proxy = self.proxy
            # Check if Username and Password are not empty
            # Set Authenticated proxy
            if not pd.isna(proxy["Username"]) and not pd.isna(proxy["Password"]):
                username = proxy["Username"]
                password = proxy["Password"]
                ip = proxy["IP"]
                port = proxy["Port"]
                manifest_json = """
                                    {
                                        "version": "1.0.0",
                                        "manifest_version": 2,
                                        "name": "Chrome Proxy",
                                        "permissions": [
                                            "proxy",
                                            "tabs",
                                            "unlimitedStorage",
                                            "storage",
                                            "<all_urls>",
                                            "webRequest",
                                            "webRequestBlocking"
                                        ],
                                        "background": {
                                            "scripts": ["background.js"]
                                        },
                                        "minimum_chrome_version":"22.0.0"
                                    }
                                    """
                background_js = """
                            var config = {
                                    mode: "fixed_servers",
                                    rules: {
                                    singleProxy: {
                                        scheme: "http",
                                        host: "%s",
                                        port: parseInt(%s)
                                    },
                                    bypassList: ["localhost"]
                                    }
                                };

                            chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

                            function callbackFn(details) {
                                return {
                                    authCredentials: {
                                        username: "%s",
                                        password: "%s"
                                    }
                                };
                            }

                            chrome.webRequest.onAuthRequired.addListener(
                                        callbackFn,
                                        {urls: ["<all_urls>"]},
                                        ['blocking']
                            );
                            """ % (ip, port, username, password)
                plugin_file = str(self.PROJECT_ROOT / f'BotRes/Plugins/proxy_auth_plugin_{username}.zip')
                plugin_manifest_file = str(self.PROJECT_ROOT / f'BotRes/Plugins/manifest_{username}.zip')
                plugin_background_file = str(self.PROJECT_ROOT / f'BotRes/Plugins/background_{username}.zip')
                with zipfile.ZipFile(plugin_file, 'w') as zp:
                    zp.writestr(plugin_manifest_file, manifest_json)
                    zp.writestr(plugin_background_file, background_js)
                options.add_extension(plugin_file)

            # Set simple proxy
            else:
                proxy = f'{proxy["IP"]}:{proxy["Port"]}'
                options.add_argument(f"--proxy-server={proxy}")
        if headless:
            options.add_argument('--headless')
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    @staticmethod
    def wait_until_visible(driver, css_selector=None, element_id=None, name=None, class_name=None, tag_name=None, duration=10000, frequency=0.01):
        if css_selector:
            WebDriverWait(driver, duration, frequency).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        elif element_id:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.ID, element_id)))
        elif name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.NAME, name)))
        elif class_name:
            WebDriverWait(driver, duration, frequency).until(
                EC.visibility_of_element_located((By.CLASS_NAME, class_name)))
        elif tag_name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.TAG_NAME, tag_name)))

    def start(self):
        try:
            self.spawn_playwright_instance()
            self.loop_and_check()
        except Exception as e:
            LOGGER.warning(e)
            LOGGER.info(f"Instance {self.id} died")
        else:
            LOGGER.info(f"{threading.current_thread().native_id} with instance no {self.id} ended gracefully")
            LOGGER.info(f"Instance {self.id} shutting down")
        finally:
            if any([self.page, self.context, self.browser]):
                self.page.close()
                self.context.close()
                self.browser.close()
                self.playwright.stop()
            self.location_info["free"] = True
    
    def loop_and_check(self):
        sleep(3)
        if self.command == 'exit':
            try:
                self.page.close()
                self.context.close()
                self.browser.close()
                self.playwright.stop()
            except:
                pass
            self.location_info['free'] = True
            return
        if self.command == 'screenshot':
            self.save_screenshot()
        if self.command == 'refresh':
            self.reload_page()
        self.command = None
    
    def save_screenshot(self):
        filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + f"_instance{self.id}.png"
        self.page.screenshot(path=filename)

    def reload_page(self):
        self.page.reload(timeout=30000)
        self.page.wait_for_selector(".persistent-player", timeout=30000)
        self.page.wait_for_timeout(1000)
        self.page.keyboard.press("Alt+t")

    def refresh_page(self):
        self.driver.refresh()
        self.wait_until_visible(self.driver, css_selector='[class="persistent-player"]', duration=10)
        self.actions.send_keys(Keys.ALT + 't')
    
    def spawn_playwright_instance(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(proxy=self.proxy, headless=self._headless, channel="chrome", args=["--window-position={},{}".format(self.location_info["x"], self.location_info["y"])])
        self.context = self.browser.new_context(user_agent=self.user_agent, viewport={"width": 800, "height": 600}, proxy=self.proxy)
        self.page = self.context.new_page()
        self.page.add_init_script("""navigator.webdriver = false;""")
        self.page.goto("https://www.twitch.tv/login", timeout=100000)
        twitch_settings = {
            "mature": "true",
            "video-muted": '{"default": "false"}',
            "volume": "0.5",
            "video-quality": '{"default": "160p30"}',
            "lowLatencyModeEnabled": "false",
        }
        try:
            self.page.click("button[data-a-target=consent-banner-accept]", timeout=15000)
        except:
            LOGGER.info("Cookie consent banner not found/clicked.")
        for key, value in twitch_settings.items():
            to_send = """window.localStorage.setItem('{key}','{value}');""".format(key=key, value=value)
            self.page.evaluate(to_send)
        self.page.set_viewport_size({"width": self.location_info["width"], "height": self.location_info["height"]})
        self.page.goto(self.target_url, timeout=60000)
        self.page.wait_for_timeout(1000)
        self.page.wait_for_selector(".persistent-player", timeout=15000)
        self.page.keyboard.press("Alt+t")
        self.page.wait_for_timeout(1000)
        self.fully_initialized = True
        self.is_watching = True
        LOGGER.info(f'{threading.current_thread().native_id} with instance no {self.id} fully initialized, using proxy {self.proxy.get("server")}')

    def spawn_selenium_instance(self):
        self.driver = self.get_driver(proxy=self.proxy, user_agent=self.user_agent, headless=self._headless)
        self.actions = ActionChains(self.driver)
        try:
            self.driver.get('https://www.twitch.tv/login')
        finally:
            pass
        
        try:
            self.wait_until_visible(self.driver, css_selector='button[data-a-target="consent-banner-accept"]', duration=20)
            self.driver.find_element(By.CSS_SELECTOR, 'button[data-a-target="consent-banner-accept"]').click()
        finally:
            pass
        
        try:
            self.wait_until_visible(self.driver, css_selector='button[aria-label="Settings"]', duration=20)
            self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Settings"]').click()
            self.wait_until_visible(self.driver, css_selector='[class="Layout-sc-nxg1ff-0 aleoz"', duration=5)
            self.driver.find_element(By.CSS_SELECTOR, '[class="Layout-sc-nxg1ff-0 aleoz"').click()
            self.wait_until_visible(self.driver, css_selector='[id="cz2XhhXWgNZqiyrnYJp1P1Zc45xiBFKm"]', duration=5)
            self.driver.find_element(By.CSS_SELECTOR, '[id="cz2XhhXWgNZqiyrnYJp1P1Zc45xiBFKm"]').click()
        finally:
            pass
        try:
            self.wait_until_visible(self.driver, '[class="persistent-player"]', 10)
        finally:
            pass
        sleep(1)
        self.actions.send_keys(Keys.ALT + 't')
        self.fully_initialized = True
        self.is_watching = True
        LOGGER.info(f'{threading.current_thread().native_id} with instance no {self.id} fully initialized, using proxy {self.proxy}')


# Screen Manager
class Screen:
    def __init__(self, window_width, window_height):
        self.window_width_offset = 100
        self.window_height_offset = 50
        self.window_width = window_width
        self.window_height = window_height
        self.screen_width = self.get_screen_resolution('width')
        self.screen_height = self.get_screen_resolution('height')
        self.spawn_locations = self.generate_spawn_locations()

    @staticmethod
    def get_screen_resolution(kind):
        try:
            import tkinter as tk
            root = tk.Tk()
        except Exception as e:
            LOGGER.info(e)
            return 500
        return_value = None
        if kind == "width":
            return_value = root.winfo_screenwidth()
        if kind == "height":
            return_value = root.winfo_screenheight()
        root.destroy()
        return return_value

    def generate_spawn_locations(self):
        spawn_locations = []
        cols = int(self.screen_width / (self.window_width - self.window_width_offset))
        rows = int(self.screen_height / (self.window_height - self.window_height_offset))
        index = 0
        for row in range(rows):
            for col in range(cols):
                spawn_locations.append(
                    {
                        "index": index,
                        "x": col * (self.window_width - self.window_width_offset),
                        "y": row * (self.window_height - self.window_height_offset),
                        "width": self.window_width,
                        "height": self.window_height,
                        "free": True})
                index += 1
        return spawn_locations
    
    def get_free_screen_location(self):
        free_keys = [screen_info for screen_info in self.spawn_locations if screen_info["free"]]
        if not free_keys:
            return None
        lowest_location_info = free_keys[0]
        lowest_location_info["free"] = False
        return lowest_location_info

    def get_default_location(self):
        return self.spawn_locations[0]


# Proxy Manager
class ProxyManager:
    def __init__(self, file_path_proxies):
        self.file_path_proxies = file_path_proxies
        self.proxy_list = self.get_proxies()

    def build_proxy_list(self):
        try:
            if self.file_path_proxies.endswith(".json"):
                raise NotImplementedError("JSON file not implemented yet")
            elif self.file_path_proxies.endswith(".txt"):
                self.build_proxy_list_txt()
            else:
                LOGGER.info("File type not supported")
        except Exception as e:
            LOGGER.warning(e)
            raise FileNotFoundError(f"Unable to find {self.file_path_proxies}")

    # Loads proxies from local CSV file
    def get_proxies(self):
        file_proxies = str(self.PROJECT_ROOT / 'BotRes/Proxies.csv')
        proxy_list = pd.read_csv(file_proxies, index_col=None)
        return [proxy for proxy in proxy_list.iloc]
    
    def get_proxy_as_dict(self):
        if not self.proxy_list:
            return {}
        proxy = self.proxy_list.pop(0)
        self.proxy_list.append(proxy)
        return proxy


# Instance Manager
class InstanceManager:
    def __init__(self, spawn_thread_count, headless, http, file_path_proxies, spawn_interval=1, view_interval=2, target_url=None):
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.file_path_user_agents = str(self.PROJECT_ROOT / 'TwitchRes/user-agents.txt')
        self.spawn_interval_seconds = spawn_interval
        self.view_interval = view_interval
        self._headless = headless
        self._http = http
        self._spawn_thread_count = spawn_thread_count
        self.target_url = target_url
        self.screen = Screen(window_width=500, window_height=300)
        self.proxies = ProxyManager(file_path_proxies)
        self.user_agents_list = self.get_user_agents()
        self.vlc_instances_dict = {}
        self.http_instances_dict = {}
        self.browser_instances_dict = {}

    def get_user_agents(self):
        try:
            with open(self.file_path_user_agents) as user_agents:
                return user_agents.read().splitlines()
        except Exception as e:
            LOGGER.warning(e)
            raise FileNotFoundError()
    
    def set_headless(self, new_value=True):
        self._headless = new_value

    def set_http(self, new_value=True):
        self._http = new_value

    def __del__(self):
        LOGGER.info('Deleting manager: cleaning up instances')
        self.delete_all_instances()
    
    def get_random_user_agent(self):
        return random.choice(self.user_agents_list)
    
    def get_active_count(self):
        if self._http:
            return len(self.http_instances_dict.keys())
        else:
            return len(self.browser_instances_dict.keys())

    def get_instances_overview(self):
        return_dict = {}
        if self._http:
            for key, instance_dict in self.http_instances_dict.items():
                return_dict[key] = instance_dict["Status"]
            return return_dict
        else:
            for key, instance_dict in self.browser_instances_dict.items():
                return_dict[key] = "Alive"
                if instance_dict["instance"].fully_initialized:
                    return_dict[key] = "Init"
                if instance_dict["instance"].is_watching:
                    return_dict[key] = "Watching"
            return return_dict

    def get_fully_initialized_count(self):
        if self._http:
            return len([True for instance in self.http_instances_dict.values() if instance["Status"] == "Init"])
        else:
            return len([True for instance in self.browser_instances_dict.values() if instance["instance"].fully_initialized])

    def spawn_instances(self, n, target_url=None):
        for _ in range(n):
            self.spawn_instance(target_url)
            time.sleep(self.spawn_interval_seconds)
    
    def spawn_instance(self, target_url=None):
        if self._http:
            threading.Thread(target=self.spawn_http_thread, args=(target_url,)).start()
        else:
            threading.Thread(target=self.spawn_instance_thread, args=(target_url,)).start()

    def spawn_instance_thread(self, target_url=None):
        if not any([target_url, self.target_url]):
            raise Exception("No target target url provided")
        with threading.Lock():
            user_agent = self.get_random_user_agent()
            proxy = self.proxies.get_proxy_as_dict()
            if self._headless:
                screen_location = self.screen.get_default_location()
            else:
                screen_location = self.screen.get_free_screen_location()
            if not screen_location:
                LOGGER.info("no screen space left")
                return
            instance_dict = dict()
            if not self.browser_instances_dict:
                instance_id = 1
            else:
                instance_id = max(self.browser_instances_dict.keys()) + 1
            self.browser_instances_dict[instance_id] = instance_dict
        if not target_url:
            target_url = self.target_url
        instance = Instance(user_agent=user_agent, target_url=target_url, proxy=proxy, location_info=screen_location, headless=self._headless, instance_id=instance_id)
        instance_dict["thread"] = threading.current_thread().native_id
        instance_dict["instance"] = instance
        instance.start()

    def http_watch(self, instance_id, proxy, target_url):
        ip_port = proxy.get('server')
        ip_username = proxy.get('username')
        ip_password = proxy.get('password')
        proxy = f'http://{ip_username}:{ip_password}@{ip_port}'
        proxies = {"http": proxy}
        self.http_instances_dict[instance_id]['Status'] = 'Watching'
        # command = f'streamlink --url {target_url} --http-proxy {proxy} -j'
        command = f'streamlink --url {target_url} -j'
        # os.system(f'streamlink --url {target_url} -j --player-args "--noaudio" --default-stream worst --player-http --hls-segment-timeout 30 --hls-segment-attempts 3 --retry-open 1 --retry-streams 1 --retry-max 1 --http-stream-timeout 3600')
        output = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0]
        watch_url = json.loads(output)['streams']['worst']['url']
        # LOGGER.info(f'Watch URL: {watch_url}')
        # sleep(500)
        while True:
            if self.http_instances_dict[instance_id]['Command'] == 'exit':
                LOGGER.info(f'Exiting instance: {self.http_instances_dict[instance_id]}')
                self.http_instances_dict.pop(instance_id)
                return
            requests.head(url=watch_url, proxies=proxies)
            sleep(5)


    def spawn_http_thread(self, target_url=None):
        if not any([target_url, self.target_url]):
            raise Exception("No target target url provided")
        with threading.Lock():
            proxy = self.proxies.get_proxy_as_dict()
            instance_dict = dict()
            if not self.http_instances_dict:
                instance_id = 1
            else:
                instance_id = max(self.http_instances_dict.keys()) + 1
            instance = threading.Thread(target=self.http_watch, args=(instance_id, proxy, target_url,))
            thread_id = threading.current_thread().native_id
            LOGGER.info(f"{thread_id} starting instance no {instance_id}")
            instance_dict["thread"] = thread_id
            instance_dict['Command'] = None
            instance_dict['Status'] = 'Init'
            self.http_instances_dict[instance_id] = instance_dict
        instance.start()

    def vlc_watch(self, instance_id, proxy, target_url):
        ip_port = proxy.get('server')
        ip_username = proxy.get('username')
        ip_password = proxy.get('password')
        proxy = f'http://{ip_username}:{ip_password}@{ip_port}'
        self.vlc_instances_dict[instance_id]['Status'] = 'Watching'
        os.system(f'streamlink --url {target_url} --http-proxy {proxy} --player-args "--noaudio" --default-stream worst --player-http --hls-segment-timeout 30 --hls-segment-attempts 3 --retry-open 1 --retry-streams 1 --retry-max 1 --http-stream-timeout 3600')
        while True:
            sleep(1)
            if self.vlc_instances_dict[instance_id]['Command'] == 'exit':
                LOGGER.info(f'Exiting instance: {self.vlc_instances_dict[instance_id]}')
                self.vlc_instances_dict.pop(instance_id)
                return

    def spawn_vlc_thread(self, target_url=None):
        if not any([target_url, self.target_url]):
            raise Exception("No target target url provided")
        with threading.Lock():
            proxy = self.proxies.get_proxy_as_dict()
            instance_dict = dict()
            if not self.vlc_instances_dict:
                instance_id = 1
            else:
                instance_id = max(self.vlc_instances_dict.keys()) + 1
            instance = threading.Thread(target=self.vlc_watch, args=(instance_id, proxy, target_url,))
            thread_id = threading.current_thread().native_id
            LOGGER.info(f"{thread_id} starting instance no {instance_id}")
            instance_dict["thread"] = thread_id
            instance_dict['Command'] = None
            instance_dict['Status'] = 'Init'
            self.vlc_instances_dict[instance_id] = instance_dict
        instance.start()
    
    def queue_screenshot(self, instance_id=None):
        if instance_id not in self.browser_instances_dict:
            return False
        self.browser_instances_dict[instance_id]['instance'].command = 'screenshot'
        LOGGER.info(f'Saved screenshot of instance id: {instance_id}')
    
    def queue_refresh(self, instance_id=None):
        if instance_id not in self.browser_instances_dict:
            return False
        LOGGER.info(f'Refreshing the instance id: {instance_id}')
        self.browser_instances_dict[instance_id]['instance'].command = 'refresh'

    def delete_specific(self, instance_id):
        if self._http:
            if instance_id not in self.http_instances_dict:
                LOGGER.info(f'Instance with id {instance_id} not found')
                return False
            LOGGER.info(f'Destroying Instance with id {instance_id}')
            self.http_instances_dict[instance_id]['Command'] = 'exit'
        else:
            if instance_id not in self.browser_instances_dict:
                LOGGER.info(f'Instance with id {instance_id} not found')
                return False
            LOGGER.info(f'Destroying Instance with id {instance_id}')
            self.browser_instances_dict[instance_id]['instance'].command = 'exit'

    def delete_latest(self):
        if self._http:
            if not self.http_instances_dict:
                LOGGER.info("No instances found")
                return
            with threading.Lock():
                latest_key = max(self.http_instances_dict.keys())
                LOGGER.info(f"Issuing shutdown of instance No. {latest_key}")
                self.http_instances_dict[latest_key]["Command"] = "exit"
        else:
            if not self.browser_instances_dict:
                LOGGER.info("No instances found")
                return
            with threading.Lock():
                latest_key = max(self.browser_instances_dict.keys())
                LOGGER.info(f"Issuing shutdown of instance No. {latest_key}")
                self.browser_instances_dict[latest_key]["instance"].command = "exit"
    
    def delete_all_instances(self):
        if self._http:
            [threading.Thread(target=self.delete_specific, args=[i + 1],).start() for i in range(len(self.http_instances_dict))]
        else:
            [threading.Thread(target=self.delete_specific, args=[i + 1],).start() for i in range(len(self.browser_instances_dict))]


class InstanceBox(tk.Frame):
    def __init__(self, manager, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.instance_id = None
        self.manager = manager
        self.bind("<Button-1>", lambda event: self.manager.queue_refresh(instance_id=self.instance_id))  # left click
        self.bind("<Button-3>", lambda event: self.manager.delete_specific(instance_id=self.instance_id))  # right click
        self.bind("<Control-1>", lambda event: self.manager.queue_screenshot(instance_id=self.instance_id))  # control left click

    def modify(self, status, instance_id):
        self.instance_id = instance_id
        color_codes = {"inactive": "SystemButtonFace", "Alive": "grey", "Init": "yellow", "Watching": "#44d209"}
        color = color_codes[status]
        self.configure(background=color)


class GUI:
    def __init__(self, manager: InstanceManager, headless: bool, http: bool):
        self.manager = manager
        self.queue_counter = 0
        self.root = tk.Tk()
        self.headless = tk.BooleanVar(value=headless)
        self.http = tk.BooleanVar(value=http)
        self.change_headmode()
        self.instances_boxes = []

    def spawn_one_func(self):
        LOGGER.info('Spawning one instance. Please wait for alive & watching instances increase.')
        target_url = self.root.children['!entry'].get()
        threading.Thread(target=self.manager.spawn_instance, args=(target_url,)).start()

    def spawn_five_func(self):
        LOGGER.info('Spawning five instances. Please wait for alive & watching instances increase.')
        target_url = self.root.children['!entry'].get()
        threading.Thread(target=self.manager.spawn_instances, args=(5, target_url,)).start()
    
    def spawn_ten_func(self):
        LOGGER.info('Spawning ten instances. Please wait for alive & watching instances increase.')
        target_url = self.root.children['!entry'].get()
        threading.Thread(target=self.manager.spawn_instances, args=(10, target_url,)).start()

    def delete_one_func(self):
        LOGGER.info('Destroying one instance. Please wait for alive & watching instances decrease.')
        threading.Thread(target=self.manager.delete_latest).start()

    def delete_all_func(self):
        LOGGER.info('Destroying all instances. Please wait for alive & watching instances decrease.')
        threading.Thread(target=self.manager.delete_all_instances).start()
    
    def change_headmode(self):
        self.manager.set_headless(self.headless.get())

    def change_http(self):
        self.manager.set_http(self.http.get())

    def run(self):
        root = self.root
        root.geometry('600x305+380+180')
        path_to_cwd = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        path_to_icon = os.path.abspath(os.path.join(path_to_cwd, 'twitch-icon.ico'))
        root.iconbitmap(path_to_icon)
        path_to_toml = os.path.abspath(os.path.join(path_to_cwd, 'pyproject.toml'))
        version = toml.load(path_to_toml)['tool']['poetry']['version']
        root.title(f'TwitchViewsBot | v{version} | Developer: AliToori')
        # separators
        separator_left = ttk.Separator(orient="vertical")
        separator_left.place(x=170, relx=0, rely=0, relwidth=0.2, relheight=0.5)
        separator_right = ttk.Separator(orient="vertical")
        separator_right.place(x=-170, relx=1, rely=0, relwidth=0.2, relheight=0.5)
        # left
        proxy_available_text = tk.Label(root, text="Proxies Available", borderwidth=2)
        proxy_available_text.place(x=40, y=10)
        proxy_available = tk.Label(root, text="0", borderwidth=2, relief="solid", width=5)
        proxy_available.place(x=70, y=40)
        lbl_buy = tk.Label(root, text="(Buy More)", fg="blue", cursor="hand2")
        lbl_buy.bind("<Button-1>", lambda event: webbrowser.open("https://www.webshare.io/"))
        lbl_buy.place(x=58, y=62)
        # Headless CheckBox
        headless_checkbox = ttk.Checkbutton(root, text="Headless", command=self.change_headmode, variable=self.headless, onvalue=True, offvalue=False)
        headless_checkbox.place(x=40, y=88)
        # VLC CheckBox
        vlc_checkbox = ttk.Checkbutton(root, text="HTTP", command=self.change_http, variable=self.http, onvalue=True, offvalue=False)
        vlc_checkbox.place(x=118, y=88)
        # right
        instances_text = tk.Label(root, text="Instances", borderwidth=2)
        instances_text.place(x=455, y=10)
        alive_instances_text = tk.Label(root, text="Alive", borderwidth=2)
        alive_instances_text.place(x=455, y=40)
        watching_instances_text = tk.Label(root, text="Watching", borderwidth=2)
        watching_instances_text.place(x=455, y=60)
        alive_instances = tk.Label(root, text=0, borderwidth=2, relief="solid", width=5)
        alive_instances.place(x=530, y=40)
        watching_instances = tk.Label(root, text=0, borderwidth=2, relief="solid", width=5)
        watching_instances.place(x=530, y=60)
        cpu_usage_text = tk.Label(root, text="CPU", borderwidth=2)
        cpu_usage_text.place(x=440, y=88)
        ram_usage_text = tk.Label(root, text="RAM", borderwidth=2)
        ram_usage_text.place(x=510, y=88)
        # mid log
        channel_url = tk.Entry(root, width=40)
        channel_url.place(x=180, y=10)
        channel_url.insert(0, 'https://www.twitch.tv/ancient_gate')

        spawn_one = tk.Button(root, width=15, anchor="w", text="Spawn 1 instance", command=lambda: self.spawn_one_func())
        spawn_one.place(x=180, y=35)

        spawn_five = tk.Button(root, width=15, anchor="w", text="Spawn 5 instances", command=lambda: self.spawn_five_func())
        spawn_five.place(x=180, y=65)

        spawn_ten = tk.Button(root, width=15, anchor="w", text="Spawn 10 instances", command=lambda: self.spawn_ten_func())
        spawn_ten.place(x=242, y=95)

        destroy_one = tk.Button(root, width=15, anchor="w", text="Destroy 1 instance", command=lambda: self.delete_one_func())
        destroy_one.place(x=305, y=35)

        destroy_all = tk.Button(root, width=15, anchor="w", text="Destroy all instances", command=lambda: self.delete_all_func())
        destroy_all.place(x=305, y=65)

        # mid text box
        text_area = ScrolledText(root, height="7", width="92", font=("regular", 8))
        text_area.place(x=20, y=125)
        id_counter = 1
        for row in range(5):
            for col in range(50):
                box = InstanceBox(self.manager, self.root, background="SystemButtonFace", bd=0.5, relief="raised", width=10, height=10)
                box.place(x=24 + col * 11, y=230 + row * 12)
                self.instances_boxes.append(box)
                id_counter += 1

        # bottom
        lbl = tk.Label(root, text=r"https://t.me/AliToori", fg="blue", cursor="hand2")
        lbl.bind("<Button-1>", lambda event: webbrowser.open(lbl.cget("text")))
        lbl.place(x=250, y=288)
        
        def refresher():
            instances_overview = self.manager.get_instances_overview()
            proxy_available.configure(text=len(self.manager.proxies.proxy_list))
            for (id, status), box in zip(instances_overview.items(), self.instances_boxes):
                box.modify(status, id)
            for index in range(len(instances_overview), len(self.instances_boxes)):
                self.instances_boxes[index].modify("inactive", None)
            alive_instances.configure(text=self.manager.get_active_count())
            watching_count = len([1 for id, status in instances_overview.items() if status == "Watching"])
            watching_instances.configure(text=str(watching_count))
            cpu_usage_text.configure(text=" {:.2f}% CPU".format(psutil.cpu_percent()))
            ram_usage_text.configure(text=" {:.2f}% RAM".format(psutil.virtual_memory().percent))
            root.after(1000, refresher)  # every x milliseconds...

        refresher()
        
        def redirector(str_input=None):
            if self.root:
                text_area.insert(tk.INSERT, str_input)
                text_area.see(tk.END)
            else:
                sys.stdout = sys.__stdout__

        # Assign redirector to STDOUT stream
        sys.stdout.write = redirector
        root.resizable(False, False)
        root.mainloop()


class TwitchViewsBot:
    def __init__(self):
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.file_settings = str(self.PROJECT_ROOT / 'TwitchRes/Settings.json')
        self.file_path_proxies = str(self.PROJECT_ROOT / 'TwitchRes/proxy_list.txt')
        self.settings = self.get_settings()

    @staticmethod
    def enable_cmd_colors():
        # Enables Windows New ANSI Support for Colored Printing on CMD
        from sys import platform
        if platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    @staticmethod
    def banner():
        pyfiglet.print_figlet(text='____________ TwitchViewsBot\n', colors='RED')
        print('Author: Ali Toori\n'
              'Telegram: https://t.me/AliToori/\n'
              '************************************************************************')

    def get_settings(self):
        """
        Creates default or loads existing settings file.
        :return: settings
        """
        if os.path.isfile(self.file_settings):
            with open(self.file_settings, 'r') as f:
                settings = json.load(f)
            return settings
        settings = {"Settings": {
            "WaitForMsg": 5
        }}
        with open(self.file_settings, 'w') as f:
            json.dump(settings, f, indent=4)
        with open(self.file_settings, 'r') as f:
            settings = json.load(f)
        return settings

    # Trial version logic
    @staticmethod
    def trial(trial_date):
        ntp_client = ntplib.NTPClient()
        try:
            response = ntp_client.request('pool.ntp.org')
            local_time = time.localtime(response.ref_time)
            current_date = time.strftime('%Y-%m-%d %H:%M:%S', local_time)
            current_date = datetime.strptime(current_date, '%Y-%m-%d %H:%M:%S')
            return trial_date > current_date
        except:
            return False

    def main(self):
        freeze_support()
        self.enable_cmd_colors()
        self.banner()
        LOGGER.info('TwitchViewsBot launched')
        trial_date = datetime.strptime('2022-11-10 23:59:59', '%Y-%m-%d %H:%M:%S')
        if self.trial(trial_date):
        # if True:
            headless = True
            http = True
            spawner_thread_count = 5
            spawn_interval = 2
            manager = InstanceManager(spawn_thread_count=spawner_thread_count, headless=headless, http=http, file_path_proxies=self.file_path_proxies, spawn_interval=spawn_interval)
            GUI(manager=manager, headless=headless, http=http).run()


if __name__ == '__main__':
    TwitchViewsBot().main()