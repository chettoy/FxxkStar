#!/usr/bin/env python

# -*- coding:utf-8 -*-

import base64
import datetime
import getpass
import json
import os
import random
import re
import bs4
import hashlib
import requests
import threading
import time
import traceback
import urllib.parse
import zstandard as zstd
from lxml import etree
from bs4 import BeautifulSoup
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import List
from collections import Counter
from fontTools.ttLib import TTFont
from Crypto.Cipher import DES
from cryptography.hazmat.primitives import padding


VERSION_NAME = "FxxkStar 0.9"

G_CONFIG = {
    # enable verbose mode
    'debug': False,

    # set language
    'language': 'zh-CN',

    # save state to file
    # includes: login state, course list, course info, chapter list, chapter info, media info
    'save_state': True,

    # If set to False, data will load from cache
    'always_request_course_list': False,
    'always_request_course_info': True,

    # Submit paper automatically if all questions are answered
    'auto_submit_work': True,

    'video_only_mode': False,
    'work_only_mode': False,
    'auto_review_mode': False,

    # Use OCR instead of glyph table based matching
    'experimental_fix_fonts': False,

    'save_paper_to_file': False,

    # enable test mode
    'test': False,
}


G_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:105.0) Gecko/20100101 Firefox/105.0",
    "Connection": "keep-alive",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
}

G_STRINGS = {
    "alt_insertimage": " - [IMG]",
    "antispider_verify": "⚠️ Anti-Spider verify",
    "correct_answer": "Correct answer: ",
    "course_list_title": "Course List",
    "error_please_relogin": "⚠️ Error: Please relogin",
    "error_response": "⚠️ Wrong response from server",
    "input_chapter_num": "Input chapter number: ",
    "input_course_num": "Input course number: ",
    "input_if_sync_video_progress": "💬 Sync video progress? (y/n): ",
    "input_phone": "Please input your phone number: ",
    "input_password": "Please input your password: ",
    "login_expired": "⚠️ Login expired, please login again",
    "login_wrong_input": "Wrong phone number or password",
    "login_reenter": "Please re-enter your phone number and password",
    "login_failed": "Login failed ⚠️",
    "login_success": "Login success ✅",
    "load_course_list_failed": "Load course list failed",
    "load_course_list_success": "Load course list success",
    "my_answer": "My Answer: ",
    "notification": "💬 Notification",
    "press_enter_to_continue": "🔞 Press Enter to continue...",
    "profile_greeting": "🌈 Hello, {name}",
    "profile_student_num": "Student number: {f[0][1]}",
    "ready_to_submit_paper": "✅ Ready to submit paper",
    "save_state_success": "Save state success",
    "score_format": "Score: {score}",
    "sign_in_status_unsign": "🔐 Sign in status: Unsigned",
    "sign_in_status_success": "✅ Sign in status: Success",
    "sign_in_status_signed_by_teacher": "✅ Sign in status: Signed by teacher",
    "sign_in_status_personal_leave2": "🔐 Sign in status: Personal leave",
    "sign_in_status_absence": "🚫 Sign in status absence",
    "sign_in_status_late": "🚫 Sign in status: Late",
    "sign_in_status_leave_early": "🚫 Sign in status: Leave early",
    "sign_in_status_expired": "🚫 Sign in status: Expired",
    "sync_video_progress_started": "Sync video progress started",
    "sync_video_progress_ended": "Sync video progress ended",
    "tag_eta": "ETA",
    "tag_total_progress": "Total Progress",
    "unfinished_chapters_title": "Unfinished Chapters",
    "welcome_message": "🌠 Welcome to FxxkStar",
}

G_STRINGS_CN = {
    "alt_insertimage": " - [图片]",
    "antispider_verify": "⚠️ 反蜘蛛验证",
    "correct_answer": "正确答案: ",
    "course_list_title": "课程列表",
    "error_please_relogin": "⚠️ 请重新登录",
    "error_response": "⚠️ 错误的响应",
    "input_chapter_num": "请输入章节编号: ",
    "input_course_num": "请输入课程编号: ",
    "input_if_sync_video_progress": "💬 是否同步视频进度? (y/n): ",
    "input_phone": "请输入您的手机号码: ",
    "input_password": "请输入您的密码: ",
    "login_expired": "⚠️ 登录过期，请重新登录",
    "login_wrong_input": "手机号或密码错误",
    "login_reenter": "请按回车重新键入账号数据",
    "login_failed": "登陆失败 ⚠️",
    "login_success": "登陆成功 ✅",
    "load_course_list_failed": "加载课程列表失败",
    "load_course_list_success": "加载课程列表成功",
    "my_answer": "我的答案: ",
    "notification": "💬 通知",
    "press_enter_to_continue": "🔞 请按回车继续...",
    "profile_greeting": "🌈 您好, {name}",
    "profile_student_num": "学号: {f[0][1]}",
    "ready_to_submit_paper": "✅ 准备提交试卷",
    "save_state_success": "保存状态成功",
    "score_format": "成绩: {score}",
    "sign_in_status_unsign": "🔐 签到状态: 未签到",
    "sign_in_status_success": "✅ 签到状态: 成功",
    "sign_in_status_signed_by_teacher": "✅ 签到状态: 老师代签",
    "sign_in_status_personal_leave2": "🔐 签到状态: 个人请假",
    "sign_in_status_absence": "🚫 签到状态: 缺勤",
    "sign_in_status_late": "🚫 签到状态: 迟到",
    "sign_in_status_leave_early": "🚫 签到状态: 早退",
    "sign_in_status_expired": "🚫 签到状态: 过期",
    "sync_video_progress_started": "同步视频进度开始",
    "sync_video_progress_ended": "同步视频进度结束",
    "tag_eta": "预计完成时间",
    "tag_total_progress": "总进度",
    "unfinished_chapters_title": "未完成章节",
    "welcome_message": "🌠 欢迎使用 FxxkStar",
}

G_VERBOSE = G_CONFIG['debug']

if G_CONFIG['language'] == 'zh-CN':
    G_STRINGS = G_STRINGS_CN


class MyError(Exception):
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return "{}({})".format(self.msg, self.code)


class MyAgent():
    def __init__(self, headers: dict, cookies: dict = {}):
        self.cookies = cookies
        self.headers = headers
        self.headers_cache = headers.copy()
        self.headers_dirty = False
        self.headers_additional_document = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1',
        }
        self.headers_additional_xhr = {
            'Accept': '*/*',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.headers_additional_iframe = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Sec-Fetch-Dest': 'iframe',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insurance-Requests': '1',
        }

    def get_cookie_str(self) -> str:
        cookie_str = ""
        for key, value in self.cookies.items():
            cookie_str += key + "=" + value + "; "
        if cookie_str.endswith("; "):
            cookie_str = cookie_str[:-2]
        return cookie_str

    def get_cookie_value(self, key: str) -> str:
        return self.cookies.get(key, "")

    def update_cookie(self, name: str, value: str) -> None:
        self.headers_dirty = True
        if value == "":
            self.cookies.pop(name, "")
        else:
            self.cookies[name] = value

    def update_cookies(self, cookies: dict) -> None:
        for key, value in cookies.items():
            self.update_cookie(key, value)

    def update_cookies_str(self, cookie_str: str) -> None:
        for cookie in cookie_str.split(";"):
            cookie = cookie.strip()
            if cookie == "":
                continue
            key, value = cookie.split("=")
            self.update_cookie(key, value)

    def build_headers(self) -> dict:
        if self.headers_dirty:
            headers = self.headers.copy()
            headers['Cookie'] = self.get_cookie_str()
            self.headers_cache = headers
            self.headers_dirty = False
            return headers.copy()
        else:
            return self.headers_cache.copy()

    def build_headers_based_on(self, given_headers: dict, additional_headers: dict = {}) -> dict:
        headers = self.build_headers()
        headers.update(given_headers)
        headers.update(additional_headers)
        return headers


class FxxkStar():
    def __init__(self, my_agent: MyAgent, saved_state: dict = {}):
        self.agent = my_agent
        self.uid: str = ""
        self.homepage_url: str = ""
        self.account_info = {}
        self.course_dict = {}
        self.course_info = {}
        self.chapter_info = {}
        self.active_info = {}
        if saved_state.__contains__("version") and saved_state['version'] == VERSION_NAME:
            if saved_state.get("cookies", None) is not None:
                self.agent.update_cookies_str(saved_state['cookies'])
            if saved_state.get("uid") is not None:
                self.uid = saved_state.get("uid")
            if saved_state.get("homepage_url") is not None:
                self.homepage_url = saved_state.get("homepage_url")
            for prop in ["account_info", "course_dict", "course_info", "chapter_info", "active_info"]:
                if saved_state.get(prop) is not None:
                    self.__setattr__(prop, saved_state.get(prop))

    def save_state(self) -> dict:
        return {
            "version": VERSION_NAME,
            "cookies": self.agent.get_cookie_str(),
            "uid": self.uid,
            "homepage_url": self.homepage_url,
            "account_info": self.account_info,
            "course_dict": self.course_dict,
            "course_info": self.course_info,
            "chapter_info": self.chapter_info,
            "active_info": self.active_info,
        }

    def get_agent(self) -> MyAgent:
        return self.agent

    def check_login(self) -> bool:
        if self.uid == "":
            _uid = self.agent.get_cookie_value("_uid")
            if _uid != "":
                self.uid = _uid
            else:
                return False
        return True

    @staticmethod
    def encrypt_by_DES(message: str, key: str) -> str:
        key_bytes = key.encode('utf-8')
        des = DES.new(key_bytes, DES.MODE_ECB)

        data = message.encode('utf-8')
        padder = padding.PKCS7(64).padder()
        padded_data = padder.update(data) + padder.finalize()

        ciphertext = des.encrypt(padded_data)
        return ciphertext.hex()

    def sign_in(self, uname: str, password: str):
        url = "https://passport2.chaoxing.com/fanyalogin"
        data = "fid=-1&uname={0}&password={1}&refer=https%3A%2F%2Fi.chaoxing.com&t=true&forbidotherlogin=0&validate=".format(
            uname, self.encrypt_by_DES(password, "u2oh6Vu^"))
        headers = self.agent.build_headers_based_on({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie': 'source=""',
            'Origin': 'https://passport2.chaoxing.com',
            'Referer': 'https://passport2.chaoxing.com/login?fid=&newversion=true&refer=https%3A%2F%2Fi.chaoxing.com',
        }, self.agent.headers_additional_xhr)
        sign_in_rsp = requests.post(url=url, data=data, headers=headers)
        sign_in_json = sign_in_rsp.json()

        if sign_in_json['status']:
            self.uid = sign_in_rsp.cookies['_uid']
            for item in sign_in_rsp.cookies:
                self.agent.update_cookie(item.name, item.value)
            return True
        else:
            if 'msg2' in sign_in_json:
                msg = sign_in_json['msg2']
                if "密码错误" == msg or "用户名或密码错误" == msg:
                    msg = G_STRINGS['login_wrong_input']
                    return False
                else:
                    raise MyError(0, msg)
            raise MyError(
                1, G_STRINGS['login_failed'] + ": " + str(sign_in_json))

    def url_302(self, from_url: str, additional_headers: dict = {}, retry=5) -> str:
        headers = self.agent.build_headers_based_on(additional_headers)

        rsp = None
        while retry >= 0:
            try:
                rsp = requests.get(
                    url=from_url, headers=headers, allow_redirects=False)
                break
            except requests.exceptions.ConnectionError as err:
                retry -= 1
                tag = "[{}] ".format(time.asctime(time.localtime(time.time())))
                print(tag, err)
                time.sleep(10)
        if rsp == None:
            raise MyError(1, "url_302: Connection Error")
        if rsp.status_code not in [302, 200, 301]:
            raise MyError(rsp.status_code,
                          G_STRINGS['error_response'] + ": url=" + from_url + "\n" + str(rsp.text))
        new_url = rsp.headers.get("Location")
        if new_url == None:
            new_url = from_url
        else:
            if G_VERBOSE:
                print("[INFO] 302 to " + new_url)
        if new_url == "https://mooc1.chaoxing.com/antispiderShowVerify.ac":
            raise MyError(0, G_STRINGS['antispider_verify'])
        return new_url

    def request(self, url: str, additional_headers: dict = {}, data=None, method="GET", retry=3) -> requests.Response:
        headers = self.agent.build_headers_based_on(additional_headers)
        rsp = None
        while retry >= 0:
            try:
                if data != None:
                    rsp = requests.request(
                        method=method, url=url, headers=headers, data=data)
                else:
                    rsp = requests.request(
                        method=method, url=url, headers=headers)
                break
            except requests.exceptions.ConnectionError as err:
                retry -= 1
                tag = "[{}] ".format(time.asctime(time.localtime(time.time())))
                print(tag, err)
                time.sleep(10)

        if rsp.status_code == 200:
            # print(rsp.text)
            for item in rsp.cookies:
                if item.name in ['actix-session']:
                    continue
                self.agent.update_cookie(item.name, item.value)
            return rsp
        else:
            raise MyError(rsp.status_code,
                          G_STRINGS['error_response'] + ": url=" + url + "\n" + str(rsp.text))

    def request_document(self, url: str, header_update: dict = {}, data=None, method="GET"):
        headers = self.agent.headers_additional_document.copy()
        headers.update(header_update)
        return self.request(url, headers)

    def request_iframe(self, url: str, header_update: dict = {}):
        headers = self.agent.headers_additional_iframe.copy()
        headers.update(header_update)
        return self.request(url, headers, method="GET")

    def request_xhr(self, url: str, header_update: dict = {}, data=None, method="GET"):
        headers = self.agent.headers_additional_xhr.copy()
        headers.update(header_update)
        return self.request(url, headers, data, method=method)

    @staticmethod
    def extract_form_fields(soup):
        "Turn a BeautifulSoup form in to a dict of fields and default values"
        fields = {}
        for input in soup.findAll('input'):
            # ignore submit/image with no name attribute
            if not input.has_attr('name'):
                continue

            # single element nome/value fields
            if input['type'] in ('text', 'hidden', 'password', 'submit', 'image'):
                value = ''
                if input.has_attr('value'):
                    value = input['value']
                fields[input['name']] = value
                continue

            # checkboxes and radios
            if input['type'] in ('checkbox', 'radio'):
                value = ''
                if input.has_attr('checked'):
                    assert input.get('checked') in ["checked", "true"]
                    if input.has_attr('value'):
                        value = input['value']
                    else:
                        value = 'on'
                    fields[input['name']] = value
                continue

            assert False, 'input type %s not supported' % input['type']

        # textareas
        for textarea in soup.findAll('textarea'):
            fields[textarea['name']] = textarea.string or ''

        # select fields
        for select in soup.findAll('select'):
            value = ''
            options = select.findAll('option')
            is_multiple = select.has_attr('multiple')
            selected_options = [
                option for option in options
                if option.has_attr('selected')
            ]

            # If no select options, go with the first one
            if not selected_options and options:
                selected_options = [options[0]]

            if not is_multiple:
                assert(len(selected_options) < 2)
                if len(selected_options) == 1:
                    value = selected_options[0]['value']
            else:
                value = [option['value'] for option in selected_options]

            fields[select['name']] = value

        return fields

    @staticmethod
    def get_time_millis() -> int:
        return int(round(time.time() * 1000))

    @staticmethod
    def sleep(duration: int, max_duration: int = 0) -> None:
        'Sleep for a random amount of milliseconds, up to max_duration'
        if duration < max_duration:
            time.sleep(random.randint(duration, max_duration) / 1000)
        else:
            time.sleep(duration / 1000)

    @staticmethod
    def format_date_like_javascript() -> str:
        # format: Fri Feb 07 1997 00:00:00 GMT+0800 (中国标准时间)
        t = datetime.datetime.utcnow() + datetime.timedelta(hours=+8)
        return t.strftime("%a %b %d %Y %H:%M:%S GMT+0800 (中国标准时间)")

    @staticmethod
    def bs_get_text_content(el: bs4.Tag) -> str:
        contents = el.contents
        if not contents:
            return ""
        text = ""
        for con in contents:
            if isinstance(con, str):
                text += con
        return text

    def get_homepage_url(self, force_update=False) -> str:
        '''
        Get the homepage url in 10 minutes
        e.g. https://i.chaoxing.com/base?t=1680307200000
        '''

        def load_homepage_url():
            url0 = "https://i.chaoxing.com"
            homepage_url = self.url_302(url0)
            homepage_html = self.request_document(homepage_url).text
            homepage_soup = BeautifulSoup(homepage_html, "lxml")
            if homepage_soup.find("title").string.strip() != "个人空间":
                raise MyError(0, G_STRINGS['error_response'] +
                              ": url=" + homepage_url + "\n" + str(homepage_html))
            assert homepage_url.startswith("https://i.chaoxing.com/base")
            self.homepage_url = homepage_url
            return homepage_url

        if self.homepage_url == "" or force_update:
            return load_homepage_url()

        url_parse = urllib.parse.urlparse(self.homepage_url)
        url_param = urllib.parse.parse_qs(url_parse.query)
        t = int(url_param.get("t")[0])
        if t < self.get_time_millis() - 1000 * 60 * 10:
            return load_homepage_url()
        else:
            return self.homepage_url

    def load_notice_count(self) -> int:
        url = "https://i.chaoxing.com/base/getNoticeCount"
        parms = {"_t": self.format_date_like_javascript()}
        resp = self.request_xhr(url, {
            "Origin": "https://i.chaoxing.com",
            "Referer": self.get_homepage_url(),
        }, parms, method="POST")
        result = resp.json()
        assert result['status'] == True
        return result['count']

    def load_profile(self) -> dict:
        homepage_url = self.get_homepage_url(force_update=True)

        self.sleep(500, 700)

        # url1 = "https://i.chaoxing.com/base/verify"
        # parms1 = {"_t": self.format_date_like_javascript()}
        # print("[INFO] load_profile verify")
        # result1 = self.request_xhr(url1, {
        #     "Origin": "https://i.chaoxing.com",
        #     "Referer": homepage_url,
        # }, data=parms1, method="POST").json()
        # if result1.get("status", False) != True:
        #     raise MyError(0, G_STRINGS['error_response'] +
        #                   ": url=" + url1 + "\n" + str(result1))

        url2 = "https://i.chaoxing.com/base/settings"
        print("[INFO] load_profile settings")
        self.request_iframe(url2, {
            "Referer": homepage_url,
        })

        self.sleep(50, 200)

        url3 = "https://passport2.chaoxing.com/mooc/accountManage"
        print("[INFO] load_profile account")
        account_page_html = self.request_iframe(url3, {
            "Referer": "https://i.chaoxing.com/",
        }).text

        if G_CONFIG['test']:
            with open("temp/debug-account_page.html", "w") as f:
                f.write(account_page_html)

        def _parse_profile(account_page_html: str):
            soup = BeautifulSoup(account_page_html, "lxml")
            title = soup.find("title").string.strip()
            assert title == "账号管理"
            info_div = soup.find("div", class_="infoDiv")
            name = info_div.find(id="messageName").string.strip()
            phone = info_div.find(id="messagePhone").string.strip()
            sex = info_div.select(".sex .check.checked")[0].get("value", None)
            if sex != None:
                sex = int(sex)
            fid_list_el = info_div.find(id="messageFid").find_all("li")
            fid_list = []
            for fid_el in fid_list_el:
                item_name: str = self.bs_get_text_content(fid_el).strip()
                value_el = fid_el.find(class_="xuehao")
                if value_el:
                    item_value: str = value_el.get_text().strip()
                    if item_value.startswith("学号/工号:"):
                        item_value = item_value[6:]
                    fid_list.append([item_name, item_value])
                else:
                    fid_list.append([item_name, None])

            return {
                "name": name,
                "sex": sex,
                "phone": phone,
                "f": fid_list,
            }

        self.account_info = _parse_profile(account_page_html)
        return self.account_info

    def load_course_list(self) -> None:
        url = "https://mooc2-ans.chaoxing.com/visit/courses/list?v=" + \
            str(self.get_time_millis())

        course_html_text = self.request_xhr(url, {
            'Accept': 'text/html, */*; q=0.01',
            'Referer': 'https://mooc2-ans.chaoxing.com/visit/interaction'
        }).text
        course_HTML = etree.HTML(course_html_text)

        list_in_html = course_HTML.xpath("//ul[@class='course-list']/li")
        if list_in_html.__len__() == 0:
            page_title = course_HTML.xpath("//title/text()")[0].strip()
            if page_title == "用户登录":
                raise MyError(9, G_STRINGS['login_expired'])
            else:
                raise MyError(
                    1, G_STRINGS['load_course_list_failed'] + ": " + course_html_text)

        i = 0
        course_dict = {}
        for course_item in list_in_html:
            try:
                course_item_name = course_item.xpath(
                    "./div[2]/h3/a/span/@title")[0]
                course_link = course_item.xpath("./div[1]/a[1]/@href")[0]
                print(course_item_name, course_link)
                i += 1
                course_dict[str(i)] = [course_item_name, course_link]
            except:
                pass
        self.course_dict = course_dict

    def load_course_info(self, url_course: str) -> dict:
        course_info = {}
        url_course_page = self.url_302(url_course)
        course_info['course_page_url'] = url_course_page
        course_HTML_text = self.request_document(url_course_page).text
        course_HTML = etree.HTML(course_HTML_text)

        try:
            course_info['courseid'] = course_HTML.xpath(
                "//input[@name='courseid']/@value")[0]
            course_info['clazzid'] = course_HTML.xpath(
                "//input[@name='clazzid']/@value")[0]
            course_info['cfid'] = course_HTML.xpath(
                "//input[@name='cfid']/@value")[0]
            course_info['bbsid'] = course_HTML.xpath(
                "//input[@name='bbsid']/@value")[0]
            course_info['cpi'] = course_HTML.xpath(
                "//input[@name='cpi']/@value")[0]
        except Exception as err:
            raise MyError(1, str(err) + "###" + course_HTML_text)

        chapters_iframe_url = "https://mooc2-ans.chaoxing.com" + \
            "/mycourse/studentcourse?courseid={courseid}&clazzid={clazzid}&cpi={cpi}&ut=s".format(
                **course_info)
        chapters_HTML_text = self.request_iframe(
            chapters_iframe_url, {"Referer": url_course_page}).text
        chapters_HTML = etree.HTML(chapters_HTML_text)

        mooc1Domain = "https://mooc1.chaoxing.com"
        enc_search = re.search(r"var enc\s*=\s*[\"'](.*?)[\"']\s*;",
                               chapters_HTML.xpath("/html/body/script[not(@src)]")[0].text)
        enc = enc_search.group(1)

        chapter_list = []
        chapters_soup = BeautifulSoup(chapters_HTML_text, "lxml")
        course_unit_list = chapters_soup.select("div.chapter_unit")
        for course_unit in course_unit_list:
            catalog_name = course_unit.select(
                "div.chapter_item div div.catalog_name span")[0].get("title")
            print("# ", catalog_name)
            chapter_items = course_unit.select(
                "div.catalog_level ul li div.chapter_item")
            if len(chapter_items) == 0:
                if G_VERBOSE:
                    print(" * ", catalog_name, " is empty")
            for chapter_item in chapter_items:
                # parse chapter number
                chapter_number_str = chapter_item.select(
                    "span.catalog_sbar")[0].get_text().strip()

                # parse chapter title
                chapter_title: str
                chapter_title_node = chapter_item.get("title", None)
                if chapter_title_node == None:
                    chapter_title = chapter_item.select(
                        "div.catalog_name")[0].contents[-1].strip()
                else:
                    chapter_title = chapter_title_node

                # parse chapter link
                transfer_url: str = ""
                course_id = None
                chapter_id = None
                clazz_id = None
                chapter_entrance_node = chapter_item.get("onclick", None)
                if chapter_entrance_node == None:
                    state_node = chapter_item.select(
                        "div.catalog_state.icon-dingshi")
                    if len(state_node) > 0:
                        # chapter is not opened
                        pass
                    elif G_CONFIG['debug']:
                        with open("temp/debug-course-chapters.html", "w") as f:
                            f.write(chapters_HTML_text)
                else:
                    chapter_entrance = chapter_entrance_node.strip()
                    # For example: "toOld('000000000', '000000000', '00000000')"
                    entrance_match = re.match(
                        r"toOld\('(.*?)',\s*'(.*?)',\s*'(.*?)'\)", chapter_entrance)
                    if entrance_match == None:
                        raise MyError(
                            1, G_STRINGS['error_response'] + ": " + course_HTML_text)
                    courseid = entrance_match.group(1)
                    knowledgeId = entrance_match.group(2)
                    clazzid = entrance_match.group(3)
                    referUrl = mooc1Domain + "/mycourse/studentstudy?chapterId=" + knowledgeId + \
                        "&courseId=" + courseid + "&clazzid=" + clazzid + "&enc=" + enc + "&mooc2=1"
                    transferUrl = mooc1Domain + "/mycourse/transfer?moocId=" + courseid + \
                        "&clazzid=" + clazzid + "&ut=s&refer=" + \
                        urllib.parse.quote(referUrl)
                    transfer_url = transferUrl
                    course_id = courseid
                    chapter_id = knowledgeId
                    clazz_id = clazzid

                unfinished_count = 0
                task_status_HTML = chapter_item.select("div.catalog_task")[0]
                task_count_node: list = task_status_HTML.select(
                    "input.knowledgeJobCount")
                if len(task_count_node) == 1:
                    unfinished_count = int(task_count_node[0].get("value"))

                chapter_info = {
                    'chapterNumber': chapter_number_str,
                    'chapterTitle': chapter_title,
                    'courseid': course_id,
                    'knowledgeId':  chapter_id,
                    'clazzid': clazz_id,
                    'transferUrl': transfer_url,
                    'unfinishedCount': unfinished_count,
                }
                chapter_list.append(chapter_info)

                chapter_mark = unfinished_count if unfinished_count > 3 else [
                    "🟢", "🟡", "🟠", "🔴"][unfinished_count]
                print(" - {} {} {} [{}]".format(chapter_mark,
                      chapter_number_str, chapter_title, chapter_id))

        course_info['chapter_list'] = chapter_list
        courseid = course_info['courseid']
        self.course_info[courseid] = course_info
        print()
        return course_info

    def get_course_by_index(self, index: int | str) -> dict:
        index = str(index)
        course_name = self.course_dict[index][0]
        course_url = self.course_dict[index][1]

        parse_result = urllib.parse.urlparse(course_url)
        course_param = urllib.parse.parse_qs(parse_result.query)
        course_id = course_param.get("courseid")[0]
        clazz_id = course_param.get("clazzid")[0]
        course_cpi = course_param.get("cpi")[0]

        if G_VERBOSE:
            print("[INFO] get_course= [{}]{}".format(course_id, course_name))
            print(course_url)
            print()

        if self.course_info.__contains__(course_id) and G_CONFIG['always_request_course_info'] == False:
            return self.course_info[course_id]
        else:
            return self.load_course_info(course_url)

    def load_active_mod(self, course_id: str) -> 'ActiveModule':
        'Refresh active list and return an ActiveModule instance'
        course_id = str(course_id)
        course_info = self.course_info[course_id]
        clazz_id = course_info['clazzid']
        cpi = course_info['cpi']
        mod = ActiveModule(self, course_id, clazz_id, cpi)
        info_key = f"{course_id}_{clazz_id}"
        if info_key not in self.active_info:
            self.active_info[info_key] = {}
        self.active_info[info_key]['activeList'] = mod.load_active_list()
        return mod

    def get_active_cache(self, course_id: str) -> dict:
        course_id = str(course_id)
        course_info = self.course_info[course_id]
        clazz_id = course_info['clazzid']
        info_key = f"{course_id}_{clazz_id}"
        if info_key not in self.active_info:
            self.active_info[info_key] = {}
        return self.active_info[info_key]

    def read_cardcount(self, chapter_page_url: str,
                       course_id: str, clazz_id: str, chapter_id: str, course_cpi: str) -> int:
        rsp_text = self.request_xhr(
            url="https://mooc1.chaoxing.com/mycourse/studentstudyAjax",
            header_update={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'https://mooc1.chaoxing.com',
                'Referer': chapter_page_url,
            },
            data="courseId={0}&clazzid={1}&chapterId={2}&cpi={3}&verificationcode=&mooc2=1".format(
                course_id, clazz_id, chapter_id, course_cpi),
            method="POST"
        ).text
        result = etree.HTML(rsp_text).xpath(
            "//input[@id='cardcount']/@value")[0]
        return int(result)

    @staticmethod
    def key_chapter(course_id, clazz_id, chapter_id) -> str:
        # key to index data in self.chapter_info
        return "{}_{}_{}".format(course_id, clazz_id, chapter_id)

    def load_chapter(self, chapter_meta: dict) -> list:
        # Example for chapter_meta
        # Generated by self.load_course_info()
        # Located in self.course_list[courseid]['chapter_list'] -> item
        # {
        #     "chapterNumber": "1.1",
        #     "chapterTitle": "第一课时",
        #     "courseid": "1111",
        #     "knowledgeId": "2222",
        #     "clazzid": "3333",
        #     "transferUrl": "https://mooc1.chaoxing.com/mycourse/transfer?moocId=1111&clazzid=3333&ut=s&refer=https%3A//mooc1.chaoxing.com/mycourse/studentstudy%3FchapterId%3D2222%26courseId%3D1111%26clazzid%3D3333%26enc%3Dffffffffffffffffffffff%26mooc2%3D1",
        #     "unfinishedCount": 4
        # }
        course_id = chapter_meta['courseid']
        clazz_id = chapter_meta['clazzid']
        chapter_id = chapter_meta['knowledgeId']
        transfer_url = chapter_meta['transferUrl']

        if (G_VERBOSE):
            print("[INFO] load_chapter ==========")
            print("|{unfinishedCount}| {chapterNumber} {chapterTitle} {knowledgeId}".format(
                **chapter_meta))
            print(chapter_meta['transferUrl'])
            print()

        chapter_page_url = self.url_302(transfer_url, {
            "Referer": "https://mooc2-ans.chaoxing.com/"
        })

        if (G_VERBOSE):
            print("got chapter_url: " + chapter_page_url)

        parse_result = urllib.parse.urlparse(chapter_page_url)
        chapter_param = urllib.parse.parse_qs(parse_result.query)
        course_cpi = chapter_param.get('cpi')[0]

        chapter_HTML_text = self.request_document(
            chapter_page_url, {"Referer": transfer_url}).text
        chapter_HTML = etree.HTML(chapter_HTML_text)
        ut_enc_search = re.search(r"var utEnc\s*=\s*[\"'](.*?)[\"']\s*;",
                                  chapter_HTML.xpath("/html/head/script[not(@src)]")[0].text)
        if ut_enc_search is None:
            test1 = etree.tostring(chapter_HTML).decode()
            test2 = chapter_HTML.xpath("/html/head/script[not(@src)]")
            test3 = chapter_HTML.xpath("/html/head/script[not(@src)]")[0].text

            raise MyError(1, "utEnc not found")
        ut_enc = ut_enc_search.group(1)

        if (G_VERBOSE):
            print("utEnc=" + ut_enc)

        card_count = self.read_cardcount(
            chapter_page_url, course_id, clazz_id, chapter_id, course_cpi)

        card_list = []
        for num in range(card_count):
            try:
                cards_url = "https://mooc1.chaoxing.com/knowledge/cards?clazzid={0}&courseid={1}&knowledgeid={2}&num={4}&ut=s&cpi={3}&v=20160407-1".format(
                    clazz_id, course_id, chapter_id, course_cpi, num)
                cards_HTML_text = self.request_iframe(cards_url, {
                    "Referer": chapter_page_url
                }).text
                scripts_text = etree.HTML(cards_HTML_text).xpath(
                    "//script[1]/text()")[0]
                pattern = re.compile(r"mArg = ({[\s\S]*)}catch")
                datas = re.findall(pattern, scripts_text)[0]
                card_args = json.loads(datas.strip()[:-1])

                card_info = {
                    'card_args': card_args,
                    'card_url': cards_url,
                }
                card_list.append(card_info)
            except Exception as err:
                print("[ERROR] {}".format(err))
                raise MyError(1, "cards_url=" + cards_url +
                              "###" + cards_HTML_text)

        chapter_info = {
            'chapter_page_url': chapter_page_url,
            'card_count': card_count,
            'ut_enc':  ut_enc,
            'cards': card_list,
        }
        key_chapter = self.key_chapter(course_id, clazz_id, chapter_id)
        self.chapter_info[key_chapter] = chapter_info
        return chapter_info

    def get_client_type(self) -> str:
        return "app" if ("ChaoXingStudy" in self.agent.headers['User-Agent']) else "pc"


class ActiveModule:
    def __init__(self, fxxkstar: FxxkStar, course_id: str, clazz_id: str, course_cpi: str):
        self.fxxkstar: FxxkStar = fxxkstar
        self.fid: str = self.fxxkstar.get_agent().get_cookie_value("fid")
        self.course_id: str = course_id
        self.clazz_id: str = clazz_id
        self.course_cpi: str = course_cpi
        self.referer: str = "https://mobilelearn.chaoxing.com/page/active/stuActiveList" + \
            "?courseid={}&clazzid={}&cpi={}&ut=s&fid={}".format(
                self.course_id, self.clazz_id, self.course_cpi, self.fid)
        self.active_list: List[dict] = []
        self.active_list1: List[dict] = []
        self.active_list2: List[dict] = []
        self.class_obj: dict = {}

    def get_active_list(self) -> List[dict]:
        if (len(self.active_list) == 0):
            self.load_active_list()
        return self.active_list.copy()

    def get_ongoing_active_list(self) -> List[dict]:
        return self.active_list1.copy()

    def load_active_list(self) -> List[dict]:
        url = "https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist" + \
            f"?fid={self.fid}&courseId={self.course_id}&classId={self.clazz_id}&_={self.fxxkstar.get_time_millis()}"
        rsp_data = self.fxxkstar.request_xhr(url, {  # jquery xhr
            "Accept": "application/json, text/plain, */*",
            "Referer": self.referer,
        }).json()
        self.check_response("load_active_list", rsp_data)

        data = rsp_data['data']
        result_list = data.get('activeList', [])
        for item in result_list:
            self.active_list.append(item)
            if 'status' in item and item['status'] == 1:
                self.active_list1.append(item)
            else:
                self.active_list2.append(item)

        reading_duration = data.get('readingDuration', 0)
        if reading_duration > 0:
            ext = data['ext']
            ext_from = ext['_from_']
        return self.active_list

    def load_class_info(self) -> None:
        url = "/v2/apis/class/getClassDetail" + \
            f"?fid={self.fid}&courseId={self.course_id}&classId={self.clazz_id}"
        rsp_data = self.api_get(url)
        self.check_response("load_class_info", rsp_data)
        self.class_obj = rsp_data['data']

    def load_topic_and_work_url(self) -> List[str]:
        url = "/v2/apis/class/getTopicAndWorkUrl?DB_STRATEGY=DEFAULT" + \
            f"&fid={self.fid}&courseId={self.course_id}&classId={self.clazz_id}&cpi={self.course_cpi}"
        rsp_data = self.api_get(url)
        self.check_response("load_topic_and_work_url", rsp_data)
        data = rsp_data['data']
        topic_icon_url = data['topicUrl']
        work_icon_url = data['workUrl']
        return [topic_icon_url, work_icon_url]

    def update_is_look(self, active_id: str | int) -> None:
        url = "/ppt/taskAPI/updateIsLook" + \
            f"?activeId={active_id}&uid={self.fxxkstar.uid}"
        rsp_data = self.api_get(url)
        self.check_response(f"update_is_look={active_id}", rsp_data)
        active = self.get_active(active_id)
        if active:
            active['isLook'] = 1

    def get_active(self, active_id: str | int) -> dict | None:
        for active in self.active_list:
            if str(active['id']) == str(active_id):
                return active
        return None

    def time_format(self, millis_timestamp) -> str:
        t = datetime.datetime.fromtimestamp(millis_timestamp / 1000)
        year = t.year
        current_year = datetime.datetime.now().year
        if year == current_year:
            return t.strftime("%m-%d %H:%M")
        else:
            return t.strftime("%Y-%m-%d %H:%M")

    def get_active_extra(self, active_id: str | int) -> dict:
        active_id = str(active_id)
        active_cache = self.fxxkstar.get_active_cache(self.course_id)
        key_extra = 'fxxkstar_active_extra'
        if key_extra not in active_cache:
            active_cache[key_extra] = {}
        cache_extra = active_cache[key_extra]
        if active_id not in cache_extra:
            cache_extra[active_id] = {}
        return cache_extra[active_id]

    def deal_active(self, active_id: str | int) -> None:
        active_id = str(active_id)
        active = self.get_active(active_id)
        if not active:
            return
        active_type = active['activeType']
        is_look = active.get('isLook', 0) == 1
        is_finish = active.get('status', 0) == 2
        extra_data = self.get_active_extra(active_id)
        if active_type == 2:  # check in
            if extra_data.get('fxxkstar_checkin_status', 0) == 1:
                return
            if not is_finish or G_CONFIG['test'] == True:
                if SignInModule(self, active_id).deal_sign_in():
                    FxxkStar.sleep(100, 200)
                    if not is_look:
                        self.update_is_look(active_id)
                extra_data['fxxkstar_checkin_status'] = 1
        elif active_type == 64:  # tencent meeting
            info = json.loads(active['content'])
            start_time = info['startTime']
            subject = info['topic']
            assert info['data']['subject'] == subject
            meeting_code = info['data']['meeting_code']

            print(f"[VooV] {start_time} {subject} {meeting_code}")

    def api_get(self, url: str) -> dict:
        if url.startswith("/"):
            url = "https://mobilelearn.chaoxing.com" + url
        return self.fxxkstar.request(url, {
            "Accept": "application/json, text/plain, */*",
            "Referer": self.referer,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }).json()

    def check_response(self, tag: str, rsp_data: dict) -> None:
        if rsp_data['result'] != 1:
            # rsp_data['errorMsg']
            raise MyError(1, G_STRINGS['error_response'] +
                          f", {tag}: {str(rsp_data)}")


class SignInModule:
    def __init__(self, active_context: ActiveModule, active_id: str) -> None:
        self.context: ActiveModule = active_context
        self.active_id: str = active_id
        self.fxxkstar: FxxkStar = self.context.fxxkstar
        self.active: dict = self.context.get_active(self.active_id)
        self.course_id: str = self.context.course_id
        self.clazz_id: str = self.context.clazz_id
        self.course_cpi: str = self.context.course_cpi
        self.fid: str = self.context.fid
        self.referer: str = "https://mobilelearn.chaoxing.com/page/sign/signIn" + \
            "?courseId={}&classId={}&activeId={}&fid={}".format(
                self.course_id, self.clazz_id, self.active_id, self.fid)
        self.active_info: dict = None
        self.attend_info: dict = None

    def load_active_info(self) -> None:
        url = "/v2/apis/active/getPPTActiveInfo" + \
            "?activeId=" + self.active_id
        rsp_data = self.api_get(url)
        self.context.check_response("load_active_info", rsp_data)
        data = rsp_data['data']
        self.active_info = data

    def load_attend_info(self) -> None:
        url = "/v2/apis/sign/getAttendInfo" + \
            "?activeId=" + self.active_id
        rsp_data = self.api_get(url)
        self.context.check_response("load_attend_info", rsp_data)
        attend = rsp_data['data']
        self.attend_info = attend

    def deal_sign_status(self, status: int) -> str:
        if status == 0:
            return G_STRINGS['sign_in_status_unsign']
        elif status == 1:
            return G_STRINGS['sign_in_status_success']
        elif status == 2:
            return G_STRINGS['sign_in_status_signed_by_teacher']
        elif status == 4:
            return G_STRINGS['sign_in_status_personal_leave2']
        elif status == 5:
            return G_STRINGS['sign_in_status_absence']
        elif status == 9:
            return G_STRINGS['sign_in_status_late']
        elif status == 10:
            return G_STRINGS['sign_in_status_leave_early']
        elif status == 11:
            return G_STRINGS['sign_in_status_expired']
        else:
            return f"sign[{status}]"

    def _sign_in(self) -> None:
        url = "/v2/apis/sign/signIn" + \
            "?activeId=" + self.active_id
        rsp_data = self.api_get(url)
        self.context.check_response("sign_in", rsp_data)

    def api_get(self, url: str) -> dict:
        if url.startswith("/"):
            url = "https://mobilelearn.chaoxing.com" + url
        return self.fxxkstar.request_xhr(url, {
            "Accept": "application/json, text/plain, */*",
            "Referer": self.referer,
        }).json()

    def print_active_info(self) -> None:
        if not self.active_info:
            return
        other_id = self.active_info['otherId']
        if other_id == 2:
            print("[SignIn] QR code sign in")
        elif other_id == 3:
            print("[SignIn] Gesture sign in")
        elif other_id == 4:
            print("[SignIn] Location sign in")
        elif other_id == 5:
            print("[SignIn] Code sign in")
        else:
            print(f"[SignIn] [{other_id}] sign in")

        now_time = self.active_info['nowTime']
        end_time = self.active_info['endTime']
        print("-->", self.context.time_format(end_time), "|")

    def deal_sign_in(self) -> int:
        '''
        Request info and try to sign in, Return status number
        0: unsign, 1: success, 2: signed by teacher, 11: expired, ...
        '''
        self.load_active_info()
        self.print_active_info()
        self.load_attend_info()
        assert self.active_info != None
        assert self.attend_info != None

        status = self.attend_info['status']
        print(self.deal_sign_status(status))
        if status != 0:
            return status
        if self.active_info['otherId'] == 0 and status == 0:
            if self.active_info['ifphoto'] == 0:
                self._sign_in()
                FxxkStar.sleep(100, 200)
                return self.deal_sign_in()  # reload


class CxUncovering:
    def __init__(self) -> None:
        self.prepare()
        glyph_file = open('glyph_map', 'rb')
        glyph_data = glyph_file.read()
        glyph_file.close()
        glyph_data = zstd.decompress(glyph_data)
        self.glyph_map = json.loads(glyph_data.decode('utf-8'))
        self.path_temp_font = "temp/cxsecret/tmp.ttf"

    def translate(self, font_path) -> list:
        glyph_map = self.glyph_map
        font = TTFont(font_path)
        xml_path = font_path.replace(".ttf", ".xml")
        font.saveXML(xml_path)
        xml_data = None
        with open(xml_path, "rb") as xml_file:
            xml_data = xml_file.read()
        parser = etree.XMLParser(remove_blank_text=True)
        xml_obj = etree.XML(xml_data, parser=parser)
        glyph_list = xml_obj.findall("glyf/TTGlyph")
        trans_list = []
        for glyph in glyph_list:
            glyph_name = glyph.attrib['name']

            glyph_data = []
            for child in glyph.getchildren():
                glyph_data.append(etree.tostring(child).decode("utf-8"))
            glyph_data_str = ''.join(glyph_data)
            hash_str = hashlib.md5(glyph_data_str.encode("utf-8")).hexdigest()

            if hash_str in glyph_map:
                text0 = glyph_name.replace("uni", "\\u").encode(
                    "utf-8").decode("unicode_escape")
                text1 = glyph_map[hash_str].replace("uni", "\\u").encode(
                    "utf-8").decode("unicode_escape")
                trans_list.append((text0, text1))

        if G_VERBOSE:
            print(trans_list)
        return trans_list

    def fix_fonts(self, html):
        secret_search = re.search(
            r"url\('data:application/font-ttf;charset=utf-8;base64,(.*?)'\)", html)
        if secret_search is None:
            return html
        secret = secret_search.group(1)
        secret = base64.b64decode(secret)
        with open(self.path_temp_font, "wb") as f:
            f.write(secret)
        text_map = self.translate(self.path_temp_font)
        for (s1, s2) in text_map:
            html = html.replace(s1, s2)
        return html

    @staticmethod
    def prepare():
        font_path = "temp/cxsecret/思源黑体.ttf"
        font_xml_path = "temp/cxsecret/思源黑体.xml"
        equivalent_ideograph_path = "temp/cxsecret/Equivalent-UnifiedIdeograph-13.0.0.json"
        output_path = "glyph_map"
        if not os.path.exists("temp"):
            os.mkdir("temp")
        if not os.path.exists("temp/cxsecret"):
            os.mkdir("temp/cxsecret")
        if not os.path.exists(output_path):
            if not os.path.exists(font_xml_path):
                font = TTFont(font_path)
                font.saveXML(font_xml_path)
            equivalent_ideograph_map = {}
            with open(equivalent_ideograph_path, "r") as f:
                equivalent_ideograph_map = json.load(f)
            xml_data = None
            with open(font_xml_path, "rb") as xml_file:
                xml_data = xml_file.read()
            parser = etree.XMLParser(remove_blank_text=True)
            xml_obj = etree.XML(xml_data, parser=parser)
            glyph_list = xml_obj.findall("glyf/TTGlyph")
            glyph_map = {}
            for glyph in glyph_list:
                glyph_name = glyph.attrib['name']
                text0 = glyph_name.replace("uni", "\\u").encode(
                    "utf-8").decode("unicode_escape") if len(glyph_name) == 7 else glyph_name

                glyph_data = []
                for child in glyph.getchildren():
                    glyph_data.append(etree.tostring(child).decode("utf-8"))
                glyph_data_str = ''.join(glyph_data)
                hash_str = hashlib.md5(
                    glyph_data_str.encode("utf-8")).hexdigest()
                if hash_str in glyph_map:
                    prev_name = glyph_map[hash_str]
                    text1 = prev_name.replace("uni", "\\u").encode(
                        "utf-8").decode("unicode_escape")
                    comp = '==' if text0 == text1 else '!='
                    print(
                        f"{hash_str} duplicated in {prev_name}({text1}) {comp} {glyph_name}({text0})")
                if text0 in equivalent_ideograph_map:
                    text0 = equivalent_ideograph_map[text0]
                    glyph_name = text0.encode("unicode_escape").decode(
                        "utf-8").replace("\\u", "uni")
                glyph_map[hash_str] = glyph_name

            # uni312A(ㄪ) -> uni4E07(万)
            glyph_map["6a1170c7233e81b04656869517a2953a"] = "uni4E07"
            # uni312C(ㄬ) -> uni5E7F(广)
            glyph_map["489517af3a6dec1b67bf00c70d26f2b1"] = "uni5E7F"

            data = json.dumps(glyph_map, ensure_ascii=False)
            data = zstd.ZstdCompressor().compress(data.encode('utf-8'))
            save_file = open(output_path, 'wb')
            save_file.write(data)
            save_file.close()


class AttachmentModule:
    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_info: dict, course_id, clazz_id, chapter_id):
        self.fxxkstar: FxxkStar = fxxkstar
        self.uid: str = fxxkstar.uid
        self.attachment_item: dict = attachment_item
        self.card_args: dict = card_info['card_args']
        self.card_url: str = card_info['card_url']
        self.course_id: str = course_id
        self.clazz_id: str = clazz_id
        self.chapter_id: str = chapter_id
        self.mid: str | None = attachment_item.get("mid", None)
        self.defaults: dict = self.card_args['defaults']
        self.job: bool = attachment_item.get("job", False)
        self.module_type: str = attachment_item.get("type")
        self.attachment_property: dict = attachment_item.get("property")


class LiveModule(AttachmentModule):
    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_info: dict, course_id, clazz_id, chapter_id):
        super().__init__(fxxkstar, attachment_item,
                         card_info, course_id, clazz_id, chapter_id)

        assert self.module_type == "live"
        self.module_url = "https://mooc1.chaoxing.com/ananas/modules/live/index.html?v=2022-0324-1900"

        self.live_set_enc = self.attachment_item['liveSetEnc']
        self.job_id = self.attachment_item['jobid']
        self.other_info = self.attachment_item['otherInfo']
        self.auth_enc = self.attachment_item['authEnc']
        self.enc = self.attachment_item['enc']
        self.a_id = self.attachment_item['aid']
        self.title = self.attachment_property['title']
        self.live_id = self.attachment_property['liveId']
        self.live = self.attachment_property['live']
        self.stream_name = self.attachment_property['streamName']
        self.vdoid = self.attachment_property['vdoid']

        print("[LiveModule] ", self.title)

        self.live_info = self._request_info()
        if self.live_info['temp'].__contains__('data') and self.live_info['temp']['data'].__contains__('mp4Url'):
            print("[LiveModule] ", self.live_info['temp']['data']['mp4Url'])

    def _request_info(self) -> dict:
        fxxkstar = self.fxxkstar
        course_id, clazz_id, chapter_id = self.course_id, self.clazz_id, self.chapter_id
        chapter_key = fxxkstar.key_chapter(course_id, clazz_id, chapter_id)
        chapter_info: dict = fxxkstar.chapter_info[chapter_key]
        chapter_page_url: str = chapter_info['chapter_page_url']
        ut_enc = chapter_info['ut_enc']
        job_id, liveid, a_id = self.job_id, self.live_id, self.a_id
        enc, live_set_enc = self.enc, self.live_set_enc
        vdoid = self.vdoid
        user_id = self.uid

        def setLiveANDCourseRelation() -> dict:
            relation_url = "https://mooc1.chaoxing.com" + \
                f"/ananas/live/relation?courseid={course_id}&knowledgeid={chapter_id}&ut=s&jobid={job_id}&aid={a_id}"
            resp1 = fxxkstar.request_xhr(relation_url, {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": self.module_url,
            })
            if G_VERBOSE:
                print(resp1.text)
            return json.loads(resp1.text)

        if vdoid:
            ut = 't' if 'teacherstudy' in chapter_page_url else 's'
            url = "https://mooc1.chaoxing.com/ananas/live/liveinfo?liveid={}&userid={}&clazzid={}&knowledgeid={}&courseid={}&jobid={}".format(
                liveid, user_id, clazz_id, chapter_id, course_id, job_id)
            rsp = fxxkstar.request_xhr(url, {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": self.module_url,
            }, method="GET")
            rsp_data = json.loads(rsp.text)
            if rsp_data['status'] == True:
                return rsp_data
            else:
                raise MyError(1, "liveid=" + liveid + " ###" + rsp.text)
        else:
            url = f"https://mooc1.chaoxing.com/api/work?api=1&workId=&jobid={job_id}&needRedirect=true&type=live&isphone=fasle"
            url += f"&knowledgeid={chapter_id}&ut={ut}&clazzId={clazz_id}&clazzId={clazz_id}"
            url += f"&enc={enc}&utenc={ut_enc}&livesetenc={live_set_enc}&courseid={course_id}"

            if G_VERBOSE:
                print(url)

            rsp = fxxkstar.request_iframe(url, {
                "Referer": self.module_url
            })
            raise MyError(1, f"liveid={liveid} no_vdoid ###" + rsp.text)

    @staticmethod
    def misson_live(fxxkstar: FxxkStar, uid, course_id, clazz_id, chapter_id, stream_name, job_id, vdoid):
        src = f"https://live.chaoxing.com/courseLive/newpclive?streamName={stream_name}&vdoid={vdoid}&width=630&height=530" + \
            f"&jobid={job_id}&userId={uid}&knowledgeid={chapter_id}&ut=s&clazzid={clazz_id}&courseid={course_id}"
        rsp = fxxkstar.request(url=src)
        rsp_HTML = etree.HTML(rsp.text)
        token_url = rsp_HTML.xpath("//iframe/@src")[0]
        if G_VERBOSE:
            print(token_url)
        token_result = urllib.parse.urlparse(token_url)
        token_data = urllib.parse.parse_qs(token_result.query)
        token = token_data.get("token")
        finish_url = "https://zhibo.chaoxing.com/live/saveCourseJob?courseId={0}&knowledgeId={1}&classId={2}&userId={3}&jobId={4}&token={5}".format(
            course_id, chapter_id, clazz_id, uid, job_id, token[0])
        finish_rsp = fxxkstar.request(url=finish_url)
        if G_VERBOSE:
            print(finish_rsp.text)

    def get_live_status(self) -> str:
        info_data = self.live_info['temp']['data']
        live_status = info_data['liveStatus']
        if_review = info_data['ifReview']
        if live_status == 0:
            return 'liveUnplayed'
        elif live_status == 1:
            return 'liveLiving'
        elif live_status == 4 and if_review == 1:
            return 'liveFinished'
        elif live_status == 4 and if_review == 0:
            return 'livePlayback'


class DocumentModule(AttachmentModule):
    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_info: dict, course_id, clazz_id, chapter_id):
        super().__init__(fxxkstar, attachment_item,
                         card_info, course_id, clazz_id, chapter_id)
        assert self.module_type == "document"

        self.other_info: str = attachment_item.get("otherInfo")
        self.jtoken: str = attachment_item.get("jtoken")
        self.name: str = self.attachment_property.get("name")
        self.object_id: str = self.attachment_property.get("objectid")

        print("[DocumentModule] ", self.name)
        self.status_data = DocumentModule._request_status(
            self.fxxkstar, self.object_id)
        print("[DocumentModule] ", self.status_data['pdf'])

        if self.job:
            jobid = attachment_item.get("jobid")
            DocumentModule._misson_doucument(fxxkstar=self.fxxkstar, course_id=course_id,
                                             clazz_id=clazz_id, chapter_id=chapter_id, jobid=jobid, jtoken=self.jtoken)

    @staticmethod
    def _request_status(fxxkstar: FxxkStar, object_id: str) -> dict:
        assert len(object_id) > 1
        status_url = "https://mooc1.chaoxing.com/ananas/status/{}?flag=normal&_dc={}".format(
            object_id, int(time.time() * 1000))
        status_rsp = fxxkstar.request_xhr(status_url, {
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/pdf/index.html?v=2022-0830-1135"
        }, method="GET")
        status_json = json.loads(status_rsp.text)
        if status_json['status'] == 'success':
            return status_json
        else:
            raise MyError(1, "object_id=" + object_id +
                          " ###" + status_rsp.text)

    @staticmethod
    def _misson_doucument(fxxkstar: FxxkStar, course_id, clazz_id, chapter_id, jobid, jtoken):
        url = "https://mooc1.chaoxing.com/ananas/job/document?jobid={}&knowledgeid={}&courseid={}&clazzid={}&jtoken={}".format(
            jobid, chapter_id, course_id, clazz_id, jtoken)
        multimedia_rsp = fxxkstar.request_xhr(url, {
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/pdf/index.html?v=2022-0830-1135"
        }, method="GET")
        print("[INFO] mission_document")
        print(multimedia_rsp.text)
        print()


class VideoModule(AttachmentModule):
    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_info: dict, course_id, clazz_id, chapter_id):
        super().__init__(fxxkstar, attachment_item,
                         card_info, course_id, clazz_id, chapter_id)
        assert self.module_type == "video"

        self.object_id: str = attachment_item.get("objectId")
        self.other_info: str = attachment_item.get("otherInfo")
        self.jobid: str = attachment_item.get("jobid")
        self.is_passed: bool = attachment_item.get("isPassed", False)
        self.name: str = self.attachment_property.get("name")

        print("[VideoModule] ", self.name)
        self.status_data = VideoModule._request_status(
            self.fxxkstar, self.object_id)
        if G_VERBOSE:
            print("[VideoModule] ", self.status_data)

    @staticmethod
    def _request_status(fxxkstar: FxxkStar, object_id: str) -> dict:
        status_url = "https://mooc1.chaoxing.com/ananas/status/{}?k=1606&flag=normal&_dc={}".format(
            object_id, int(time.time() * 1000))
        status_rsp = fxxkstar.request_xhr(status_url, {
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/video/index.html?v=2022-0909-2029"
        }, method="GET")
        status_json = json.loads(status_rsp.text)
        if status_json['status'] == "success":
            return status_json
        elif status_json['status'] == "waiting":
            if G_VERBOSE:
                print("video", object_id, "response=waiting")
            return status_json
        else:
            if G_VERBOSE:
                print("[ERROR] status_json={}".format(status_json))
            raise MyError(1, "object_id= " + object_id +
                          " ###" + status_rsp.text)

    def can_play(self) -> bool:
        return self.status_data['status'] == "success"

    def get_duration(self) -> int:
        return int(self.status_data['duration'])

    def gen_report_url(self, playing_time, is_drag=0) -> str | None:
        if not self.can_play():
            return None

        duration = self.get_duration()
        dtoken = self.status_data.get('dtoken')
        report_url_base = self.defaults['reportUrl']
        if G_VERBOSE:
            print("video._gen_report_url", self.object_id, self.other_info,
                  self.jobid, self.uid, self.name, duration, report_url_base)
            print()

        report_enc = VideoModule.encode_enc(
            self.clazz_id, int(duration), self.object_id, self.other_info, self.jobid, self.uid, str(playing_time))
        other_args = "/{0}?clazzId={1}&playingTime={2}&duration={3}&clipTime=0_{3}&objectId={4}&otherInfo={5}&jobid={6}&userid={7}&isdrag={8}&view=pc&enc={9}&rt=0.9&dtype=Video&_t={10}".format(
            dtoken, self.clazz_id, playing_time, duration, self.object_id, self.other_info, self.jobid, self.uid, is_drag, report_enc, int(time.time() * 1000))
        report_url_result = report_url_base + other_args

        return report_url_result

    @staticmethod
    def encode_enc(clazzid: str, duration: int, objectId: str, otherinfo: str, jobid: str, userid: str, currentTimeSec: str):
        data = "[{0}][{1}][{2}][{3}][{4}][{5}][{6}][0_{7}]".format(clazzid, userid, jobid, objectId, int(
            currentTimeSec) * 1000, "d_yHJ!$pdA~5", duration * 1000, duration)
        if G_VERBOSE:
            print("[INFO] encode_enc=" + data)
        return hashlib.md5(data.encode()).hexdigest()


class WorkModule(AttachmentModule):
    # module/work/index.html?v=2021-0927-1700
    # referer updated: 2022-0714-1515

    cx_uncovering = None

    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_info: dict, course_id: str, clazz_id: str, chapter_id: str):
        super().__init__(fxxkstar, attachment_item,
                         card_info, course_id, clazz_id, chapter_id)
        assert self.module_type == "workid"

        # init static cx_uncovering
        if WorkModule.cx_uncovering is None:
            print("[INFO] init cx_uncovering")
            WorkModule.cx_uncovering = CxUncovering()

        self.work_id: str = self.attachment_property['workid']
        self.jobid: str = self.attachment_property['jobid']
        self.title: str = self.attachment_property['title']
        print("[WorkModule] ", self.title, self.work_id)

        self.is_marked: bool = None
        self.paper_html: str = ""
        self._load()
        if G_CONFIG['save_paper_to_file']:
            suffix = "_1" if self.is_marked else ""
            file_name = f"work_{self.work_id}{suffix}.html"
            with open(f"temp/work/{file_name}", "w") as f:
                f.write(self.paper_html)
            print("[Work] ", self.title, file_name, " saved")

        self.paper = self.parse_paper(self.paper_html, self.cx_uncovering)
        self._answers.save(
            fxxkstar, self.paper.questions, self.work_id, self.card_url)

    def _load(self):
        chapter_key = self.fxxkstar.key_chapter(
            self.course_id, self.clazz_id, self.chapter_id)
        chapter_info: dict = self.fxxkstar.chapter_info[chapter_key]
        chapter_page_url: str = chapter_info['chapter_page_url']
        utenc = chapter_info['ut_enc']

        setting: dict = self.card_args
        defaults: dict = self.defaults
        attachment: dict = self.attachment_item
        attachment_property: dict = self.attachment_property
        jobid: str = self.jobid
        workid: str = self.work_id

        if attachment_property.__contains__('schoolid'):
            workid = "{}-{}".format(attachment_property['schoolid'], workid)

        src: str = "https://mooc1.chaoxing.com" + \
            f"/api/work?api=1&workId={workid}&jobid={jobid}&needRedirect=true"

        if defaults and defaults.__contains__('knowledgeid') and defaults['knowledgeid']:
            knowledgeid = defaults['knowledgeid']
            ktoken = defaults['ktoken'] or ''
            course_id = defaults['courseid'] or ''
            cpi = defaults['cpi'] or ''
            src = src + f"&knowledgeid={knowledgeid}&ktoken={ktoken}&cpi={cpi}"

        if setting.__contains__('control') and setting['control']:
            worktype = attachment_property['worktype']
            if defaults and defaults.__contains__('knowledgeid') and defaults['knowledgeid']:
                clazzId = defaults['clazzId'] or ''
                ut = 't' if 'teacherstudy' in chapter_page_url else 's'
                ut = 't' if 'comparecard' in chapter_page_url else ut
                if 'visitnodedetail' in chapter_page_url:
                    ut = defaults['ut']
                src = src + f"&ut={ut}&clazzId={clazzId}&type=" + \
                    ('b' if worktype == 'workB' else '')

        enc = attachment['enc']
        src += f"&enc={enc}&utenc={utenc}"

        if setting['mooc2'] and setting['mooc2'] == 1:
            src += "&mooc2=1"

        src += f"&courseid={course_id}"

        if 'castscreen=1' in chapter_page_url:
            src = src.replace('/api/work', '/castscreen/chapterwork-look')

        if G_VERBOSE:
            print("[INFO] module_work, src=" + src)

        headers = self.fxxkstar.get_agent().build_headers_based_on(self.fxxkstar.get_agent().headers_additional_iframe, {
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/work/index.html?v=2022-0714-1515&castscreen=0"
        })
        src2 = self.fxxkstar.url_302(src, headers)
        src3 = self.fxxkstar.url_302(src2, headers)
        work_HTML_text = self.fxxkstar.request(src3, headers).text
        if G_VERBOSE:
            print()
        self.is_marked = "selectWorkQuestionYiPiYue" in src3
        self.paper_html = work_HTML_text
        return work_HTML_text

    class PaperInfo:
        is_marked: bool
        score: float = -1.0
        questions: List[dict] = []

    @staticmethod
    def parse_paper(paper_page_html: str, cx_uncovering: 'CxUncovering') -> PaperInfo:
        "Parse the page html"

        @dataclass
        class OptionItem:
            option: str
            content: str

        @dataclass
        class QuestionItem:
            topic: str
            type: int
            answers: List[OptionItem] | None = None
            correct: List[OptionItem] | None = None
            wrong: List[OptionItem] | None = None
            selected: List[OptionItem] = None
            question_id: str | None = None

        @dataclass
        class MarkResultItem:
            answer: str = ""
            correct_answer: str | None = None
            is_correct: bool | None = None

        soup = BeautifulSoup(paper_page_html, "lxml")
        if soup.find("div", class_="font-cxsecret"):
            if G_VERBOSE:
                print("[DEBUG] detect secret font")
            if G_CONFIG['experimental_fix_fonts']:
                paper_page_html = experimental_fix_ttf(paper_page_html)
            else:
                paper_page_html = cx_uncovering.fix_fonts(paper_page_html)
            soup = BeautifulSoup(paper_page_html, "lxml")

        # Parse paper status
        top_div = soup.find("div", class_="ZyTop")
        status_el = top_div.select("h3 span")
        status_title = status_el[0].text.strip() if status_el else ''
        assert status_title in ["待做", "已完成", "未达到及格线，请重做"]
        marked = status_title == "已完成"
        score = -1

        # Parse score
        if marked:
            # [ <span style="font-size:16px;top:25px;color:#db2727;padding-left:5px;">已完成</span>,
            #   <span style="font-size:16px;top:25px;float:right;">本次成绩：<span style="color: #000">100</span></span>,
            #   <span style="color: #000">100</span> ]
            if len(status_el) == 3:
                score = float(status_el[2].text.strip())
                score_str = str(score)
                if score_str.endswith(".0"):
                    score_str = score_str[:-2]
                assert f"本次成绩：{score_str}" in status_el[1].text.strip()

        # Find all question elements
        q_div = soup.find("div", id="ZyBottom")
        question_divs = q_div.find_all("div", class_="TiMu")
        title_tags = [["单选题", "Single Choice"], ["多选题"], ["填空题", "Fill in the Blank"], [
            "判断题", "True or False"], ["简答题", "Short Answer"], ["名词解释", "Definitions"], ["论述题"], ["计算题"]]
        questions = []
        for question_div in question_divs:
            question_title = question_div.select(
                ".Zy_TItle > .clearfix,.Cy_TItle > .clearfix")[0].get_text().strip()

            # parse question_type from tag
            question_tag = ""
            question_type = -1
            match_question_tag = re.match(
                "^[\[【]([\s\S]+?)[\]】]\s*([\s\S]+)\s*$", question_title)
            if match_question_tag:
                question_tag = match_question_tag.group(1)
                question_title = match_question_tag.group(2)
            for i in range(len(title_tags)):
                if question_tag in title_tags[i]:
                    question_type = i
                    break
            if question_type == -1:
                if question_tag == "Cloze":
                    question_type = 14
                elif question_tag == "Speaking":
                    question_type = 18

            match_score = re.match(
                "^\s*([\s\S]+?)\s*[\(（]\S+?分[\)）]$", question_title)
            if match_score:
                question_title = match_score.group(1)

            question = QuestionItem(question_title, question_type)
            mark_result = MarkResultItem()

            if not marked:
                # parse question_id and verify question_type
                answertype_node = question_div.find(
                    "input", id=re.compile("answertype"))
                if question.type != -1:
                    assert question.type == int(answertype_node.get("value"))
                else:
                    question.type = int(answertype_node.get("value"))
                    if question_tag not in ["Others"]:
                        print("[WARN] unknown question type: [{}]={}".format(
                            question_tag, question.type))
                question_id = answertype_node.get("id")[10:]
                question.question_id = question_id

            else:
                # parse my answer and correct answer
                if question.type != 2:  # Fill in the blanks has multiple results
                    answer_el = question_div.select(".Py_answer")[0]
                    answer_mark_el = answer_el.select("i.fr")
                    if answer_mark_el:
                        answer_mark_classlist: list = answer_mark_el[0].get(
                            "class")
                        if "cuo" in answer_mark_classlist:
                            mark_result.is_correct = False
                        elif "dui" in answer_mark_classlist:
                            mark_result.is_correct = True
                        elif "bandui" in answer_mark_classlist:
                            mark_result.is_correct = False
                        else:
                            assert False
                    answer_result_el = answer_el.select("span")
                    assert len(answer_result_el) > 0
                    answer: str = answer_result_el[0].text.strip()
                    if answer.startswith("正确答案："):
                        mark_result.correct_answer = answer[len(
                            "正确答案："):].strip()
                        assert len(answer_result_el) >= 2
                        answer = answer_result_el[1].text.strip()
                        assert answer.startswith("我的答案：")
                    elif answer.startswith("我的答案："):
                        pass
                    else:
                        assert False
                    mark_result.answer = answer[len("我的答案："):].strip()

            # parse options

            # for fill in the blanks
            index_list = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

            if question.type in [0, 1]:  # Choice
                options: List[OptionItem] = []
                selected: List[OptionItem] = []
                option_nodes = question_div.select("ul.Zy_ulTop li")

                if marked:
                    for option_node in option_nodes:
                        option: str = option_node.select(
                            "i.fl")[0].text.strip()
                        content: str = option_node.select(
                            "a.fl")[0].text.strip()
                        assert len(option) == 2 and option.endswith("、")  # A、
                        option = option[:-1]
                        option_info = OptionItem(option, content)
                        options.append(option_info)

                    not_selected: List[OptionItem] = []
                    for option_info in options:
                        if option_info.option in mark_result.answer:
                            selected.append(option_info)
                        else:
                            not_selected.append(option_info)

                    if mark_result.correct_answer:
                        correct_options: List[OptionItem] = []
                        for option_info in options:
                            if option_info.option in mark_result.correct_answer:
                                correct_options.append(option_info)
                        question.correct = correct_options
                    elif mark_result.is_correct is not None:
                        if mark_result.is_correct:
                            question.correct = selected
                        else:
                            if question.type == 0:
                                question.wrong = selected

                    assert len(selected) == len(mark_result.answer)
                else:
                    for option_node in option_nodes:
                        option_input_node = option_node.select(
                            "label.fl.before input")[0]
                        option = option_input_node.get("value")
                        content = option_node.select("a.fl.after")[
                            0].text.strip()
                        option_info = OptionItem(option, content)
                        options.append(option_info)
                        if option_input_node.get("checked") in ["true", "checked"]:
                            selected.append(option_info)
                question.answers = options
                if selected.__len__() > 0:
                    question.selected = selected

            elif question.type == 3:  # Judge
                selected: List[OptionItem] = []
                if marked:
                    answer = mark_result.answer
                    assert answer == "√" or answer == "×"
                    if answer == "√":
                        selected.append(OptionItem(True, True))
                    elif answer == "×":
                        selected.append(OptionItem(False, False))
                    if mark_result.is_correct is not None:
                        if mark_result.is_correct:
                            question.correct = selected.copy()
                        else:
                            correct_judge = not selected[0].option
                            question.correct = [
                                OptionItem(correct_judge, correct_judge)
                            ]
                    assert len(selected) == 1
                else:
                    choices_node = question_div.find_all(
                        "input", attrs={"name": f"answer{question.question_id}"})
                    assert len(choices_node) == 2
                    for choice_node in choices_node:
                        if choice_node.get("checked") in ["true", "checked"]:
                            judge = choice_node.get("value")
                            assert judge in ["true", "false"]
                            if judge == "true":
                                selected.append(OptionItem(True, True))
                            elif judge == "false":
                                selected.append(OptionItem(False, False))
                            break
                if len(selected) > 0:
                    question.selected = selected

            elif question.type == 2:  # Fill in the blanks
                if marked:
                    answer_el = question_div.select(".Py_answer")[0]
                    answer_result_els = answer_el.select(".clearfix")
                    assert len(answer_result_els) > 0

                    correct_el = question_div.select(".Py_tk")
                    correct_answer_els = []
                    if correct_el:
                        correct_el = correct_el[0]
                        correct_answer_els = correct_el.select(".clearfix")

                    assert len(correct_answer_els) == 0 or len(
                        correct_answer_els) == len(answer_result_els)

                    results: List[MarkResultItem] = []
                    for i, answer_result_el in enumerate(answer_result_els):
                        answer: str = answer_result_el.text.strip()
                        result = MarkResultItem(answer)

                        if correct_answer_els:
                            correct_answer_el = correct_answer_els[i]
                            result.correct_answer = correct_answer_el.text.strip()

                        answer_mark_el = answer_result_el.select("i.fr")
                        if answer_mark_el:
                            answer_mark_classlist: list = answer_mark_el[0].get(
                                "class")
                            if "dui" in answer_mark_classlist:
                                result.is_correct = True
                            elif "cuo" in answer_mark_classlist:
                                result.is_correct = False
                            else:
                                assert False
                        results.append(result)

                    current_answers: List[OptionItem] = []
                    correct_answers: List[OptionItem] = []
                    for i, result in enumerate(results):
                        option_item = OptionItem(index_list[i], result.answer)
                        current_answers.append(option_item)
                        if result.correct_answer:
                            correct_answers.append(OptionItem(
                                index_list[i], result.correct_answer))
                        elif result.is_correct == True:
                            correct_answers.append(result)
                    if len(current_answers) > 0:
                        question.selected = current_answers
                    if len(correct_answers) > 0:
                        question.correct = correct_answers

                else:
                    current_answers: List[OptionItem] = []
                    for i in range(11):
                        input_node = question_div.find(
                            "textarea", attrs={"name": f"answerEditor{question.question_id}{i+1}"})
                        if not input_node:
                            break
                        con = input_node.string
                        if con:
                            current_answers.append(
                                OptionItem(index_list[i], con.strip()))
                    assert len(current_answers) <= 10
                    if current_answers:
                        question.selected = current_answers

            elif question.type in [4, 5, 6, 7, 8, 18]:  # Short answer
                content: str = None
                if marked:
                    content = mark_result.answer
                else:
                    input_node = question_div.find(
                        "textarea", attrs={"name": f"answer{question.question_id}"})
                    assert input_node is not None
                    content = input_node.string.strip() if input_node.string else None

                if content:
                    question.selected = [OptionItem("一", content)]

                if mark_result.correct_answer:
                    question.correct = [
                        OptionItem("一", mark_result.correct_answer)
                    ]
                elif mark_result.is_correct == True:
                    question.correct = question.selected.copy()

            else:
                print("not support question type:", question.type)

            question_properties = {}
            for key, value in question.__dict__.items():
                if value == None:
                    continue
                if isinstance(value, list):
                    list_dict = []
                    for item in value:
                        list_dict.append(item.__dict__ if isinstance(
                            item, OptionItem) else item)
                    question_properties[key] = list_dict
                else:
                    question_properties[key] = value

            questions.append(question_properties)

        paper_info = WorkModule.PaperInfo()
        paper_info.is_marked = marked
        paper_info.score = score
        paper_info.questions = questions
        return paper_info

    @staticmethod
    def render_paper(paper_page_html: str, questions_state: List[dict]) -> str:
        "Render the selected answers in question dict to the page html"
        soup = BeautifulSoup(paper_page_html, "lxml")
        form1 = soup.find("form", id="form1")
        for question in questions_state:
            q_type: int = question['type']
            q_id = question['question_id']
            q_topic = question['topic']
            answers: List[dict] = question.get('selected', [])
            if q_type == 0:  # single choice
                answer_option = answers[0]['option'] if answers.__len__(
                ) > 0 else None
                for option_node in form1.find_all(attrs={"name": f"answer{q_id}"}):
                    if option_node['value'] == answer_option:
                        option_node['checked'] = "true"
                    else:
                        del option_node['checked']
            elif q_type == 1:  # multiple choice
                check_values = form1.find_all(
                    attrs={"name": f"answercheck{q_id}"})
                check_radio_value = ""
                for answer in answers:
                    check_radio_value += answer['option']
                for check_value in check_values:
                    if check_value['value'] in check_radio_value:
                        check_value['checked'] = "true"
                    else:
                        del check_value['checked']
                form1.find(id=f"answer{q_id}")['value'] = check_radio_value
            elif q_type == 3:  # judgment
                answer_judgment = answers[0]['option'] if len(
                    answers) > 0 else ""
                for option_node in form1.find_all(attrs={"name": f"answer{q_id}"}):
                    if str(option_node['value']).lower() == str(answer_judgment).lower():
                        option_node['checked'] = "true"
                    else:
                        del option_node['checked']
            elif q_type == 2:  # fill in the blanks
                count = len(answers)
                for i in range(0, count):
                    option_node = form1.find(
                        "textarea", attrs={"name": f"answerEditor{q_id}{i+1}"})
                    assert option_node is not None
                    if len(answers) > 0:
                        option_node.string = answers[i]['content']
                    else:
                        option_node.string = ""
            elif q_type in [4, 5, 6, 7, 8, 18]:  # short answer
                option_node_find = form1.find_all(
                    "textarea", attrs={"name": f"answer{q_id}"})
                assert len(option_node_find) == 1
                option_node = option_node_find[0]
                if len(answers) > 0:
                    option_node.string = answers[0]['content']
                else:
                    option_node.string = ""
            else:
                print("not support question type:", q_type)
        return soup.decode()

    @staticmethod
    def review_paper(paper: PaperInfo) -> None:
        "Display the paper in review mode"

        if G_VERBOSE:
            print(paper.questions)

        if paper.is_marked and paper.score != -1.0:
            score = "💯" if paper.score == 100 else str(paper.score)
            print(G_STRINGS['score_format'].format(score=score))

        SYM_CORRECT = "✔️"  # "√"
        SYM_WRONG = "❌"  # "×"
        print("+" + "-" * 46)
        for question in paper.questions:
            q_type: int = question['type']
            q_topic = question['topic']
            options = question.get('answers', [])
            answers = question.get('selected', [])
            correct = question.get('correct', None)
            wrong = question.get('wrong', None)

            print(f"| {q_topic}")

            if q_type == 0 or q_type == 1:  # choice
                answer_options_o = set()
                for item in answers:
                    answer_options_o.add(item['option'])

                correct_options_o = set()
                wrong_options_o = set()
                if correct != None:
                    for item in correct:
                        correct_options_o.add(item['option'])
                    if q_type == 0:
                        # Single-choice options are all incorrect except for the correct option
                        for item in options:
                            if item['option'] not in correct_options_o:
                                wrong_options_o.add(item['option'])

                if wrong != None:
                    for item in wrong:
                        wrong_options_o.add(item['option'])

                for option_item in options:
                    sym_mark = ""

                    if option_item['option'] in correct_options_o:
                        sym_mark = SYM_CORRECT
                    elif option_item['option'] in wrong_options_o:
                        sym_mark = SYM_WRONG

                    if option_item['option'] in answer_options_o:
                        print(
                            f"| [{option_item['option']}] {option_item['content']} {sym_mark}")
                    else:
                        print(
                            f"|  {option_item['option']}. {option_item['content']} {sym_mark}")
            elif q_type == 3:  # judgment
                answer_str = G_STRINGS['my_answer']
                if answers != None and len(answers) > 0:
                    answer_judgment = answers[0]['option']
                    if answer_judgment == True:
                        answer_str += SYM_CORRECT
                    elif answer_judgment == False:
                        answer_str += SYM_WRONG
                else:
                    answer_str += "____"

                sym_mark = ""
                if correct != None and len(correct) > 0:
                    correct_judgment = correct[0]['option']
                    if correct_judgment == True:
                        sym_mark = SYM_CORRECT
                    elif correct_judgment == False:
                        sym_mark = SYM_WRONG
                    else:
                        assert False
                if not answers and not correct:
                    print(f"| ____")
                else:
                    print("| ", sym_mark, "\t", answer_str)
            elif q_type == 2:  # fill in blanks
                if not answers and not correct:
                    print("| ____")
                else:
                    answer_count = len(answers) if answers else 0
                    correct_count = len(correct) if correct else 0
                    max_count = max(answer_count, correct_count)
                    common_count = min(answer_count, correct_count)
                    for i in range(max_count):
                        if i < common_count:
                            print("| ", answers[i]['content'], "\t",
                                  G_STRINGS['correct_answer'], correct[i]['content'])
                        continue
                        if answer_count > i:
                            print(
                                "| ", G_STRINGS['my_answer'], answers[i]['content'])
                        if correct_count > i:
                            print(
                                "| ", G_STRINGS['correct_answer'], correct[i]['content'])
            elif q_type in [4, 5, 6, 7, 8, 18]:  # short answer
                if not answers and not correct:
                    print("| ____")
                else:
                    if answers != None and len(answers) > 0:
                        print("| ", answers[0]['content'])
                    if correct != None and len(correct) > 0:
                        print(
                            "| ", G_STRINGS['correct_answer'], correct[0]['content'])
            else:
                print("not support question type:", q_type)

            print("+" + "-" * 46)
            if not paper.is_marked:
                FxxkStar.sleep(1200, 1600)
        print()

    @staticmethod
    def chaoxing_type_to_banktype(chaoxing_type: int) -> int:
        "Convert the question type of chaoxing to the type of answerbank"
        # 0: Single Choice, 1: Multiple Choice, 2: Fill in the Blank, 3: Judgment, 4: Short answer questions | chaoxing
        # 1: Single Choice, 2: Multiple Choice, 3: Judgment, 4: Fill in the Blank | answerbank
        translate_map = {
            0: 1,
            1: 2,
            2: 4,
            3: 3,
            4: 4,
            5: 4,
            6: 4,
            7: 4,
            8: 4,
            18: 4,
        }
        return translate_map.get(chaoxing_type, -1)

    @staticmethod
    def banktype_to_chaoxing_type(banktype: int) -> int:
        "Convert the question type of answerbank to the type of chaoxing"
        translate_map = {
            1: 0,
            2: 1,
            4: 2,
            3: 3,
        }
        return translate_map[banktype]

    @staticmethod
    def random_answer(question_state: dict) -> dict:
        "Randomly select answers in the question dict"
        question = question_state.copy()
        q_type = question['type']
        answer = []
        if q_type == 0:
            answer.append(random.choice(question['answers']))
        elif q_type == 1:
            for option in question['answers']:
                if random.random() > 0.5:
                    answer.append(option)
        elif q_type == 2:
            answer.append({"option": "一", "content": "test2"})
        elif q_type == 3:
            judgement_options = [
                {"option": True, "content": True},
                {"option": False, "content": False}
            ]
            answer.append(random.choice(judgement_options))
        elif q_type in [4, 5, 6, 7, 8, 18]:
            answer.append({"option": "一", "content": "test"})
        question['selected'] = answer
        return question

    @staticmethod
    def normalize_topic(topic: str) -> str:
        "Normalize the topic name"

        translate = [
            ("，", ","),
            ("。", "."),
            ("？", "?"),
            ("！", "!"),
            ("：", ":"),
            ("；", ";"),
            ("（", "("),
            ("）", ")"),
            ("～", "~"),
            ("‘", "'"),
            ("’", "'"),
            ("“", "\""),
            ("”", "\""),
            ("－", "-"),
            ("／", "/"),
            ("＝", "="),
            ("＜", "<"),
            ("＞", ">"),
            ("＊", "*"),
            ("＋", "+"),
            ("％", "%"),
            ("｜", "|"),
            ("｛", "{"),
            ("｝", "}"),
            ("［", "["),
            ("］", "]"),
            ("．", "."),
            ("\r\n", "\n"),
        ]
        for (src, dst) in translate:
            topic = topic.replace(src, dst)

        topic = re.sub("\s+", " ", topic).strip()

        return topic

    @staticmethod
    def compare_option_content(option_a: dict, option_b: dict) -> bool:
        "Compare the content of two options"
        str1: str = option_a['content']
        str2: str = option_b['content']

        # Remove the spaces and compare
        if str1.strip() == str2.strip():
            return True

        # Remove html tags and compare
        soup1 = BeautifulSoup(str1, "lxml")
        soup2 = BeautifulSoup(str2, "lxml")
        str1 = soup1.get_text().strip()
        str2 = soup2.get_text().strip()
        if str1 == str2:
            return True

        # Uniform punctuation and then compare
        str1 = WorkModule.normalize_topic(str1)
        str2 = WorkModule.normalize_topic(str2)
        if str1 == str2:
            return True

        return False

    @staticmethod
    def fix_answers_option(question: dict, key_answers='selected') -> None:
        "Regenerate the answer according to the options of the question"
        if question['type'] not in [0, 1]:
            return
        options = question['answers']
        answers = question[key_answers]
        new_answers = []
        for option in options:
            for answer in answers:
                if WorkModule.compare_option_content(option, answer):
                    new_answers.append(option)
                    break
        if len(new_answers) < len(answers):
            raise MyError(2, "fix answers warning:" + str(question))
        question[key_answers] = new_answers

    @staticmethod
    def _validate(fxxkstar: FxxkStar, course_id: str, clazz_id: str, cpi: str) -> bool:
        ajax_url = "https://mooc1.chaoxing.com/work/validate?courseId={}&classId={}&cpi={}".format(
            course_id, clazz_id, cpi)
        rsp_text = fxxkstar.request_xhr(ajax_url, {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/work/index.html?v=2022-0714-1515&castscreen=0",
        }).text
        # {"status":3}
        if G_VERBOSE:
            print("[INFO] work_validate, rsp_text=" + rsp_text)
        result = json.loads(rsp_text)
        status = result['status']
        if status == 1:
            # Failure
            raise MyError(1, "work_validate, status=1")
        elif status == 2:
            # Show verification code
            print("[WARN] work_validate, show verification code")
            return True
        elif status == 3:
            # Normal
            print(G_STRINGS['ready_to_submit_paper'])
            return True
        else:
            raise MyError(G_STRINGS['error_response'] +
                          ", url=" + ajax_url + " ### " + rsp_text)

    @staticmethod
    def module_work_submit(fxxkstar: FxxkStar, work_page_html: str, do_submit=False) -> bool:
        soup = BeautifulSoup(work_page_html, "lxml")
        form1 = soup.find("form", id="form1")
        course_id = soup.find(id="courseId").get("value")
        class_id = soup.find(id="classId").get("value")
        cpi = soup.find(id="cpi").get("value")
        enc_work = soup.find(id="enc_work").get("value")
        total_question_num = soup.find(id="totalQuestionNum").get("value")

        parms = FxxkStar.extract_form_fields(form1)
        answer_all_id = ""
        for key in parms:
            if key.startswith("answertype"):
                answer_all_id += key[10:] + ","
        parms['answerwqbid'] = answer_all_id
        if do_submit:
            if WorkModule._validate(fxxkstar, course_id, class_id, cpi):
                # wait 0.2s ~ 1s before submit
                time.sleep(random.randint(200, 1000)/1000)
            else:
                return False
        else:
            parms['pyFlag'] = "1"

        ajax_url = "https://mooc1.chaoxing.com" + \
            f"/work/addStudentWorkNew?_classId={class_id}&courseid={course_id}&token={enc_work}&totalQuestionNum={total_question_num}"
        ajax_type = form1.get("method") or "post"
        ajax_data = urllib.parse.urlencode(parms)
        if not do_submit:
            ajax_url += "&pyFlag=1"
        ajax_url += f"&ua={fxxkstar.get_client_type()}"
        ajax_url += f"&formType={ajax_type}"
        ajax_url += "&saveStatus=1"
        ajax_url += "&version=1"

        rsp_text = fxxkstar.request_xhr(ajax_url, {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/work/index.html?v=2022-0714-1515&castscreen=0",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }, data=ajax_data, method=ajax_type).text
        # {"msg":"保存成功！","status":true}
        if G_VERBOSE:
            print("[INFO] module_work_submit, rsp_text=" + rsp_text)
        result = json.loads(rsp_text)
        if result['status'] == True:
            print('✅', result['msg'])
            return True
        else:
            raise MyError(result['msg'] + " " + rsp_text)

    def correct_answers(self, questions: List[dict], work_id: str, card_url: str) -> List[dict]:
        "Set correct answers in question dict, return a list of unprocessed questions"

        def apply_result(resp_result: dict, questions: dict) -> None:
            key_correct_options = "correct"
            unprocessed_list: List[dict] = []
            for topic_result in resp_result:
                index = topic_result['index']
                result = topic_result['result']
                topic = questions[index]['topic']
                prev_answers = questions[index].get(key_correct_options, None)

                def use_prev_answers():
                    if prev_answers is None:
                        if key_correct_options in questions[index]:
                            del questions[index][key_correct_options]
                    else:
                        questions[index][key_correct_options] = prev_answers
                    unprocessed_list.append(questions[index])

                if result and len(result) > 0:
                    if len(result) > 1:
                        print(f"{topic} has {len(result)}results")
                        found_right_result = False
                        for r in result:
                            try:
                                questions[index][key_correct_options] = r['correct']
                                self.fix_answers_option(
                                    questions[index], key_correct_options)
                                found_right_result = True
                                break
                            except MyError as e:
                                use_prev_answers()
                                pass
                        if not found_right_result:
                            if G_VERBOSE:
                                print(result)
                            raise MyError(2, f"{topic} has no right result")
                    else:
                        questions[index][key_correct_options] = result[0]['correct']
                        try:
                            self.fix_answers_option(
                                questions[index], key_correct_options)
                        except MyError as e:
                            use_prev_answers()
                            print(e)
                else:
                    print(f"{topic} no_answer")
                    unprocessed_list.append(questions[index])
            return unprocessed_list

        resp_result = self._answers.req(
            self.fxxkstar, questions, work_id, card_url)
        unprocessed_list = apply_result(resp_result, questions)
        if len(unprocessed_list) == 0:
            return []
        FxxkStar.sleep(200)

        unprocessed_list2 = []
        for question in unprocessed_list:
            result = self._answers.find2(question)
            if apply_result(result, [question]):
                unprocessed_list2.append(question)
            FxxkStar.sleep(500, 1000)

        return unprocessed_list2

    def upload_answers(self, answers: List[dict], confirm_submit=False) -> bool:
        "Save or submit the answers"
        if G_VERBOSE:
            print("[INFO] upload_answers, answers=" + str(answers))
        answered_html = WorkModule.render_paper(self.paper_html, answers)
        if WorkModule.module_work_submit(self.fxxkstar, answered_html, do_submit=confirm_submit):
            time.sleep(0.2)
            if confirm_submit:
                self._load()  # reload the page to get the result
                self.paper = WorkModule.parse_paper(
                    self.paper_html, self.cx_uncovering)
                WorkModule._answers.save(
                    self.fxxkstar, self.paper.questions, self.work_id, self.card_url)
            return True
        else:
            return False

    class _answers:
        @staticmethod
        def _info(work_id: str, card_url: str):
            return json.dumps({
                "refer": card_url,
                "id": work_id,
                "info": work_id,
            })

        @staticmethod
        def save(fxxkstar: FxxkStar, questions: List[dict], work_id: str, card_url: str) -> None:
            count = len(questions)
            if count <= 20:
                __class__._save_20(fxxkstar, questions, work_id, card_url)
                return
            remaining_questions = questions.copy()
            while len(remaining_questions) > 20:
                batch_questions = remaining_questions[:20]
                remaining_questions = remaining_questions[20:]
                __class__._save_20(
                    fxxkstar, batch_questions, work_id, card_url)
                FxxkStar.sleep(50)
            if len(remaining_questions) > 0:
                __class__._save_20(
                    fxxkstar, remaining_questions, work_id, card_url)
            print("[INFO] _answers.save, finish count=" + str(count))

        @staticmethod
        def _save_20(fxxkstar: FxxkStar, questions: List[dict], work_id: str, card_url: str) -> None:
            data = []
            for item in questions:
                correct = item.get('correct', None)
                wrong = item.get('wrong', None)
                if not correct and not wrong:
                    continue

                topic = item.get('topic')
                r_type = WorkModule.chaoxing_type_to_banktype(item.get('type'))
                if r_type == -1:
                    continue
                assert isinstance(topic, str)
                assert isinstance(r_type, int)

                save_item = {
                    "topic": topic,
                    "type": r_type,
                    "correct": correct,
                    "wrong": wrong,
                }
                if not correct:
                    del save_item['correct']
                if not wrong:
                    del save_item['wrong']
                data.append(save_item)

            if len(data) == 0:
                return

            serialized_str: str = urllib.parse.urlencode({
                "info": __class__._info(work_id, card_url),
                "data": json.dumps(data),
            })
            if G_VERBOSE:
                print("[DEBUG] _answer.save, serialized_str=" + serialized_str)
            print("answers saved")

        @staticmethod
        def req(fxxkstar: FxxkStar, questions: List[dict], work_id: str, card_url: str) -> List[dict]:
            return []

        @staticmethod
        def find2(question: dict | str) -> list:
            return []


class video_report_action:

    def __init__(self, video_mod: VideoModule):
        self.multimedia_headers: dict = video_mod.fxxkstar.get_agent().build_headers_based_on(
            video_mod.fxxkstar.get_agent().headers_additional_xhr, {
                'Accept': '*/*',
                'Content-Type': 'application/json',
                'Referer': 'https://mooc1.chaoxing.com/ananas/modules/video/index.html?v=2022-0909-2029',
            })
        self.clazz_id: str = video_mod.clazz_id
        self.duration: int = video_mod.get_duration()
        self.jobid: str = video_mod.jobid
        self.object_id: str = video_mod.object_id
        self.other_info: str = video_mod.other_info
        self.uid: str = video_mod.uid
        self.total_time: int = self.duration
        self.video_mod: VideoModule = video_mod

    def run(self) -> None:
        self.name = threading.current_thread().name

        # report play start
        rsp = requests.get(url=self.video_mod.gen_report_url(
            playing_time=0, is_drag=3), headers=self.multimedia_headers)
        print("▶️", self.video_mod.name, rsp.text)
        if rsp.status_code != 200:
            raise MyError(rsp.status_code, rsp.text)

        # update cookies
        cookieTmp = self.multimedia_headers['Cookie']
        for item in rsp.cookies:
            cookieTmp = cookieTmp + '; ' + item.name + '=' + item.value
        self.multimedia_headers.update({"Cookie": cookieTmp})

        # print progress
        print("⏳[%s] %s 0/%d" %
              (self.name, self.video_mod.name, self.total_time))

        # report play progress
        time_now = 0
        while self.total_time - time_now > 60:
            time.sleep(60)
            time_now = time_now + 60
            rsp = requests.get(url=self.video_mod.gen_report_url(
                time_now), headers=self.multimedia_headers)
            print("⏳[%s] %s %d/%d" %
                  (self.name, self.video_mod.name, time_now, self.total_time))
            if G_VERBOSE:
                print(self.name, rsp.text)
        time.sleep(self.total_time - time_now)

        # report play end
        rsp = requests.get(url=self.video_mod.gen_report_url(
            self.total_time, is_drag=4), headers=self.multimedia_headers)
        print("⌛[%s] %s %s" % (self.name, self.video_mod.name, rsp.text))
        if rsp.json().get('isPassed') == True:
            print("✅ %s" % (self.video_mod.name))


class FxxkStarHelper():
    def __init__(self, fxxkstar: FxxkStar):
        self.fxxkstar: FxxkStar = fxxkstar
        self.unfinished_chapters: List[dict] = []
        self.video_to_watch: List[VideoModule] = []

    @staticmethod
    def start_interactive_login(fxxkstar: FxxkStar) -> None:
        sign_sus = False
        while sign_sus == False:
            uname = input(G_STRINGS['input_phone'])
            password = getpass.getpass(G_STRINGS['input_password'])
            sign_sus = fxxkstar.sign_in(uname, password)
            if sign_sus == False:
                print(G_STRINGS['login_reenter'])
                print(G_STRINGS['press_enter_to_continue'])
                input()

    def login_if_need(self) -> str:
        if self.fxxkstar.check_login() == False:
            self.start_interactive_login(self.fxxkstar)
            time.sleep(2)
            # force reload course list after login
            G_CONFIG['always_request_course_list'] = True
        return self.fxxkstar.uid

    def show_profile(self) -> dict:
        if self.fxxkstar.account_info == {} or G_CONFIG['test']:
            self.fxxkstar.load_profile()
        profile = self.fxxkstar.account_info
        print(G_STRINGS['profile_greeting'].format(**profile))
        print(G_STRINGS['profile_student_num'].format(**profile))
        return profile

    def load_courses_if_need(self) -> dict:
        if self.fxxkstar.course_dict == {} or G_CONFIG['always_request_course_list']:
            self.fxxkstar.load_course_list()
            print(G_STRINGS['load_course_list_success'])
            time.sleep(3)
        return self.fxxkstar.course_dict

    def print_course_list(self) -> dict:
        course_dict: dict = self.fxxkstar.course_dict
        title = G_STRINGS['course_list_title']
        print()
        print(f"== {title} ==" + "=" * (20 - len(title)))
        for num in course_dict:
            course = course_dict[num]
            print(f"{num} {course[0]}")
        print("=" * 26)
        print()
        return course_dict

    @staticmethod
    def select_unfinished_chapters(chapters: dict) -> dict:
        title = G_STRINGS['unfinished_chapters_title']
        print()
        print(f"== {title} ==" + "=" * (20 - len(title)))
        unfinished_chapters = []
        for chapter in chapters:
            point_count = chapter['unfinishedCount']
            if point_count > 0:
                unfinished_chapters.append(chapter)
                print("「{}」 {} {}".format(
                    point_count, chapter['chapterNumber'], chapter['chapterTitle']))

        print("=" * 26)
        print()
        return unfinished_chapters

    def medias_deal(self, card_info: dict, course_id: str, clazz_id: str, chapter_id: str) -> None:
        card_args = card_info['card_args']
        card_url = card_info['card_url']
        attachments_json = card_args['attachments']
        defaults_json = card_args['defaults']

        assert str(defaults_json['courseid']) == course_id
        assert str(defaults_json['clazzId']) == clazz_id
        assert str(defaults_json['knowledgeid']) == chapter_id

        for attachment_item in attachments_json:
            attachment_type = attachment_item.get("type")

            if G_CONFIG['video_only_mode'] and attachment_type != "video":
                continue
            if G_CONFIG['work_only_mode'] or G_CONFIG['auto_review_mode'] and attachment_type != "workid":
                continue

            if attachment_type == "document":
                mod = DocumentModule(self.fxxkstar, attachment_item,
                                     card_info, course_id, clazz_id, chapter_id)

            elif attachment_type == "live":
                mod = LiveModule(self.fxxkstar, attachment_item,
                                 card_info, course_id, clazz_id, chapter_id)

            elif attachment_type == "video":
                mod = VideoModule(self.fxxkstar, attachment_item,
                                  card_info, course_id, clazz_id, chapter_id)

                if mod.can_play() and not mod.is_passed:
                    self.video_to_watch.append(mod)

            elif attachment_type == "workid":
                mod = WorkModule(self.fxxkstar, attachment_item=attachment_item, card_info=card_info,
                                 course_id=course_id, clazz_id=clazz_id, chapter_id=chapter_id)

                if G_CONFIG['auto_review_mode']:
                    continue

                if mod.paper.is_marked:
                    WorkModule.review_paper(mod.paper)
                else:
                    prev_answer_map = {}
                    for question in mod.paper.questions:
                        prev_answer_map[question['question_id']
                                        ] = question.get('selected', [])
                    uncertain_questions = mod.correct_answers(
                        mod.paper.questions, mod.work_id, card_url)
                    fast_forward = 'ff' in G_CONFIG['magic']
                    if not fast_forward:
                        mod.review_paper(mod.paper)
                        FxxkStar.sleep(1000)

                    save_answers = False
                    for q in mod.paper.questions:
                        if q.get('correct', None):
                            q['selected'] = q['correct']
                        if q.get('selected', []) != prev_answer_map[q['question_id']]:
                            save_answers = True
                    if save_answers:
                        if fast_forward:
                            mod.review_paper(mod.paper)
                        FxxkStar.sleep(1000, 4000)
                        confirm_submit = G_CONFIG['auto_submit_work'] and len(
                            uncertain_questions) == 0
                        mod.upload_answers(
                            mod.paper.questions, confirm_submit)
                        if mod.paper.is_marked:
                            mod.review_paper(mod.paper)
                    elif G_VERBOSE:
                        print("[Work] ", mod.title, mod.work_id, "no change")

            else:
                if G_VERBOSE:
                    print("attachment_item", attachment_item)

                if 'property' in attachment_item:
                    attachment_property = attachment_item['property']
                    if 'module' in attachment_property:
                        module_type = attachment_property['module']
                        if module_type == "insertbook":
                            print("[InsertBook]",
                                  attachment_property['bookname'])
                            print("[InsertBook]",
                                  attachment_property['readurl'])
                        elif module_type == "insertimage":
                            print(G_STRINGS['alt_insertimage'])
                        else:
                            print(module_type)
                else:
                    if not G_VERBOSE:
                        print("attachment_item", attachment_item)

    def deal_chapter(self, chapter_meta: dict) -> None:
        chapter_info = self.fxxkstar.load_chapter(chapter_meta)
        for num in range(chapter_info['card_count']):
            FxxkStar.sleep(500, 1500)
            card_info = chapter_info['cards'][num]
            self.medias_deal(
                card_info, chapter_meta['courseid'], chapter_meta['clazzid'], chapter_meta['knowledgeId'])

    def get_cookies(self) -> str:
        return self.fxxkstar.get_agent().get_cookie_str()

    def sync_video_progress(self, thread_count=3) -> None:
        thread_pool = ThreadPoolExecutor(max_workers=thread_count)
        future_list: List[Future] = []

        def print_eta(i: int, total: int) -> None:
            if i > total:
                total = i
            print()
            print(f"{G_STRINGS['tag_total_progress']}: {i}/{total}")
            # [####------] 100.0%
            print(
                f"[{'#' * int(i / total * 20)}{'-' * (20 - int(i / total * 20))}] {round(i / total * 100, 2)}%")
            print()

        def calc_eta() -> int:
            duration_list = []
            for item in self.video_to_watch:
                duration_list.append(item.get_duration())

            simu_list = []
            eta = len(duration_list) * 2
            while len(duration_list) > 0:
                while len(duration_list) > 0 and len(simu_list) < thread_count:
                    simu_list.append(duration_list.pop(0))
                current_duration = min(simu_list)
                simu_list = map(lambda x: x - current_duration, simu_list)
                eta += current_duration
                simu_list = list(filter(lambda x: x > 0, simu_list))
            eta += max(simu_list)

            return eta

        eta = calc_eta()
        print(f"[{G_STRINGS['tag_eta']}] {eta//60}min {eta%60}s")
        print(G_STRINGS['sync_video_progress_started'])

        start_time = FxxkStar.get_time_millis()

        def run_task(video_mod: VideoModule):
            video_report_action(video_mod).run()

        def dispatch_task():
            def on_done(future: Future):
                future_list.remove(future)
                now = FxxkStar.get_time_millis()
                print_eta((now - start_time)//1000, eta)
                time.sleep(1)
                dispatch_task()
            while self.video_to_watch and len(future_list) < thread_count:
                video_item: VideoModule = self.video_to_watch.pop(0)
                future = thread_pool.submit(run_task, video_item)
                future_list.append(future)
                future.add_done_callback(on_done)
                time.sleep(1)

        dispatch_task()
        while len(future_list) > 0:
            future_list[0].result()

        thread_pool.shutdown()
        print(G_STRINGS['sync_video_progress_ended'])
        print()

    def check_notification(self, course_id: str) -> None:
        active_mod = self.fxxkstar.load_active_mod(course_id)
        active_list = None
        if G_CONFIG['test'] == True:
            active_list = active_mod.get_active_list()
        else:
            active_list = active_mod.get_ongoing_active_list()
        if len(active_list) > 0:
            print(G_STRINGS['notification'])
            print("-" * 20)
            for active in active_list:
                print("* [%s] %s" % (active['nameFour'], active['nameOne']))
                active_mod.deal_active(active['id'])
                FxxkStar.sleep(400, 500)
            print("-" * 20)
        print()

    def choose_course_and_study(self) -> None:
        self.print_course_list()
        choose_course = input(G_STRINGS['input_course_num'])
        print()

        course = self.fxxkstar.get_course_by_index(choose_course)

        print()
        self.check_notification(course['courseid'])
        time.sleep(2)

        chapters = course['chapter_list']
        auto_review = G_CONFIG['auto_review_mode']

        unfinished_chapters = chapters if auto_review else self.select_unfinished_chapters(
            chapters)
        time.sleep(1)

        chose_chapter_index = -1
        autotest = auto_review
        while True:
            choose_chapter = ''

            if autotest:
                FxxkStar.sleep(1000, 5000)
            else:
                choose_chapter = input(G_STRINGS['input_chapter_num']).strip()

            if choose_chapter == 'q' or choose_chapter == 'Q':
                break
            if choose_chapter == 'autotest':
                autotest = True
                choose_chapter = "next"

            if choose_chapter == "n" or choose_chapter == "next" or choose_chapter == '':
                choose_chapter = chose_chapter_index + 1
            else:
                if choose_chapter.isdigit():
                    choose_chapter = int(choose_chapter) - 1

            print()
            current_chapter = None
            if isinstance(choose_chapter, int):
                # select by the index of unfinished_chapters
                if 0 <= choose_chapter < unfinished_chapters.__len__():
                    current_chapter = unfinished_chapters[choose_chapter]
                    chose_chapter_index = choose_chapter
                else:
                    break
            else:
                # select by chapter_number
                # find in unfinished_chapters and set chose_chapter_index
                for i, chapter in enumerate(unfinished_chapters):
                    if chapter['chapterNumber'] == choose_chapter:
                        current_chapter = chapter
                        chose_chapter_index = i
                        break
                # or find in all chapters
                if current_chapter is None:
                    for chapter in chapters:
                        if chapter['chapterNumber'] == choose_chapter:
                            current_chapter = chapter
                            break
                # or quit
                if current_chapter is None:
                    break

            print()
            print(
                f"⚪ {current_chapter['chapterNumber']} {current_chapter['chapterTitle']}")
            self.deal_chapter(current_chapter)
            print()


def experimental_fix_ttf(html_text: str):

    from PIL import Image, ImageDraw, ImageFont
    import pytesseract

    def translate(font_path) -> list:
        font = TTFont(font_path)
        image_font = ImageFont.truetype(font_path, size=40)
        glyph_list = []
        utext_list = []

        for name in font.getGlyphOrder():
            if name == '.notdef':
                continue
            u_text = ""
            if name[:3] == 'uni':
                u_text = name.replace('uni', '\\u')
            elif name[:2] == 'uF':
                u_text = name.replace('uF', '\\u')
            else:
                continue
            u_text = json.loads(f'"{u_text}"')
            #print(name, u_text)
            glyph_list.append(name)
            utext_list.append(u_text)

        t_dict = {}
        for u_text in utext_list:
            t_dict[u_text] = []

        utext_remains = utext_list.copy()
        group_index = 0
        group_max = (len(utext_list) / 15 + 1) * 4
        width = 15
        while True:
            process_list = []
            while len(utext_remains) < width:
                utext_remains.extend(utext_list)
            for i in range(width):
                process_list.append(utext_remains.pop(0))
            random.shuffle(process_list)

            image_path1 = f"temp/cxsecret/img/{group_index}.png"
            image_path2 = f"temp/cxsecret/img/{group_index}_r.png"

            current_result = recog_glyph(process_list, image_font, image_path1)
            reverse_process = process_list.copy()
            reverse_process.reverse()
            current_result2 = recog_glyph(
                reverse_process, image_font, image_path2)
            current_result2.reverse()
            read_len = min(len(current_result), len(current_result2))
            failed_list = []
            for i in range(len(process_list)):
                if i < read_len and current_result[i] == current_result2[i]:
                    u_text = current_result[i][0]
                    t_list = t_dict.get(u_text)
                    t_list.append(current_result[i][1])
                    if len(t_list) > 3 and u_text in utext_list and len(utext_list) > 5:
                        utext_list.remove(u_text)
                else:
                    failed_list.append(process_list[i])
            utext_remains.extend(failed_list)
            group_index += 1
            if group_index > group_max / 2:
                width = 10
            if group_index > group_max:
                break
        result = []
        for u_text, t_list in t_dict.items():
            counter = Counter(t_list)
            print(u_text, counter)
            best = counter.most_common(1)[0][0]
            result.append((u_text, best))

        return result

    def recog_glyph(utext_list, image_font, image_path) -> list:

        img = Image.new(mode='L', size=(40*len(utext_list), 40), color=255)
        draw = ImageDraw.Draw(img)
        for i, u_text in enumerate(utext_list):
            draw.text((i*40, 0), u_text, font=image_font, fill=0)

        img.save(image_path)
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang="chi_sim")
        if not text:
            text = pytesseract.image_to_string(
                img, lang="chi_sim", config='--psm 10')
        text = text.strip().replace('\n', '').replace(' ', '')
        print(text)
        print(len(text), len(utext_list))
        if len(text) == len(utext_list):
            text_list = list(text)
            result = []
            for i, u_text in enumerate(utext_list):
                result.append((utext_list[i], text_list[i]))
            return result
        else:
            return []

    def fix_fonts(html):
        secret_search = re.search(
            r"url\('data:application/font-ttf;charset=utf-8;base64,(.*?)'\)", html)
        secret = secret_search.group(1)
        secret = base64.b64decode(secret)
        with open("temp/cxsecret/tmp.ttf", "wb") as f:
            f.write(secret)
        text_map = translate("temp/cxsecret/tmp.ttf")
        # for (s1, s2) in text_map:
        #     print(s1, "->", s2)
        for (s1, s2) in text_map:
            html = html.replace(s1, s2)
        return html

    return fix_fonts(html_text)


def before_start() -> None:
    "print some info before start"
    print()
    print(G_STRINGS['welcome_message'])
    print("Repo: https://github.com/chettoy/FxxkStar")
    print()
    print("## Acknowledgments --")
    print("+------------------------------------------------------------+")
    print("| [chaoxing_tool](https://github.com/liuyunfz/chaoxing_tool) |")
    print("| [cxmooc-tools](https://github.com/CodFrm/cxmooc-tools)     |")
    print("| [FxxkSsxx](https://github.com/chettoy/FxxkSsxx)            |")
    print("+------------------------------------------------------------+")
    print()
    input(G_STRINGS['press_enter_to_continue'])
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print()


def read_state_from_file() -> dict:
    saved_file = open('star.json.zst', 'rb')
    saved_data = saved_file.read()
    saved_file.close()
    saved_data = zstd.decompress(saved_data)
    saved_data = json.loads(saved_data.decode('utf-8'))
    return saved_data


def save_state_to_file(fxxkstar: FxxkStar) -> None:
    data = json.dumps(fxxkstar.save_state(), ensure_ascii=False)
    data = zstd.ZstdCompressor().compress(data.encode('utf-8'))
    save_file = open('star.json.zst', 'wb')
    save_file.write(data)
    save_file.close()
    print(G_STRINGS['save_state_success'])


def prepare() -> FxxkStar:
    agent = MyAgent(G_HEADERS)
    try:
        saved_data = read_state_from_file()
        return FxxkStar(agent, saved_data)
    except FileNotFoundError:
        return FxxkStar(agent)


if __name__ == "__main__":
    before_start()
    fxxkstar = None
    try:
        fxxkstar = prepare()

        helper = FxxkStarHelper(fxxkstar)
        helper.login_if_need()
        helper.show_profile()
        print()
        time.sleep(1.5)

        helper.load_courses_if_need()

        if G_CONFIG['save_state'] and fxxkstar is not None:
            save_state_to_file(fxxkstar)

        helper.choose_course_and_study()

        if input(G_STRINGS['input_if_sync_video_progress']) == 'y':
            helper.sync_video_progress(5)

    except Exception as err:
        tag = "[{}] ".format(time.asctime(time.localtime(time.time())))
        print(tag, traceback.format_exc())
        print(err)
        if isinstance(err, MyError) and err.code == 9:
            fxxkstar.uid = ""
            fxxkstar.get_agent().cookies = {}
        if G_CONFIG['save_state'] and fxxkstar is not None:
            save_state_to_file(fxxkstar)
        input()
    finally:
        if G_CONFIG['save_state'] and fxxkstar is not None:
            save_state_to_file(fxxkstar)
        print()
        input(G_STRINGS['press_enter_to_continue'])
