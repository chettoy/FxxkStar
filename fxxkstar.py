#!/usr/bin/env python

# -*- coding:utf-8 -*-

import base64
import getpass
import json
import random
import re
import requests
import threading
import time
import traceback
import urllib.parse
from lxml import etree
from bs4 import BeautifulSoup
from typing import List


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
}


G_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:99.0) Gecko/20100101 Firefox/99.0",
    "Connection": "keep-alive",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
}

G_STRINGS = {
    "antispider_verify": "Anti-Spider verify",
    "course_list_title": "Course List",
    "error_response": "Wrong response from server",
    "input_chapter_num": "Input chapter number: ",
    "input_course_num": "Input course number: ",
    "input_if_sync_video_progress": "Sync video progress? (y/n): ",
    "input_phone": "Please input your phone number: ",
    "input_password": "Please input your password: ",
    "login_wrong_input": "Wrong phone number or password",
    "login_reenter": "Please re-enter your phone number and password",
    "login_failed": "Login failed",
    "login_success": "Login Success",
    "load_course_list_failed": "Load course list failed",
    "load_course_list_success": "Load course list success",
    "press_enter_to_continue": "Press Enter to continue...",
    "save_state_success": "Save state success",
    "sync_video_progress_started": "Sync video progress started",
    "sync_video_progress_ended": "Sync video progress ended",
    "unfinished_chapters_title": "Unfinished Chapters",
    "welcome_message": "Welcome to FxxkStar",
}

G_STRINGS_CN = {
    "antispider_verify": "反蜘蛛验证",
    "course_list_title": "课程列表",
    "error_response": "错误的响应",
    "input_chapter_num": "请输入章节编号: ",
    "input_course_num": "请输入课程编号: ",
    "input_if_sync_video_progress": "是否同步视频进度? (y/n): ",
    "input_phone": "请输入您的手机号码: ",
    "input_password": "请输入您的密码: ",
    "login_wrong_input": "手机号或密码错误",
    "login_reenter": "请按回车重新键入账号数据",
    "login_failed": "登陆失败",
    "login_success": "登陆成功",
    "load_course_list_failed": "加载课程列表失败",
    "load_course_list_success": "加载课程列表成功",
    "press_enter_to_continue": "请按回车继续...",
    "save_state_success": "保存状态成功",
    "sync_video_progress_started": "同步视频进度开始",
    "sync_video_progress_ended": "同步视频进度结束",
    "unfinished_chapters_title": "未完成章节",
    "welcome_message": "欢迎使用 FxxkStar",
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
            key, value = cookie.strip().split("=")
            self.update_cookie(key, value)

    def build_headers(self) -> dict:
        if self.headers_dirty:
            headers = self.headers.copy()
            headers["Cookie"] = self.get_cookie_str()
            self.headers_cache = headers
            self.headers_dirty = False
            return headers
        else:
            return self.headers_cache

    def build_headers_based_on(self, given_headers: dict, additional_headers: dict = {}) -> dict:
        headers = self.build_headers()
        headers.update(given_headers)
        headers.update(additional_headers)
        return headers


class FxxkStar():
    def __init__(self, my_agent: MyAgent, saved_state: dict = {}):
        self.agent = my_agent
        self.uid = -1
        self.course_dict = {}
        self.course_info = {}
        self.chapter_info = {}
        if saved_state.__contains__("version") and saved_state["version"] == VERSION_NAME:
            if saved_state.get("cookies", None) is not None:
                self.agent.update_cookies_str(saved_state["cookies"])
            if saved_state.get("uid") is not None:
                self.uid = saved_state.get("uid")
            if saved_state.get("course_dict") is not None:
                self.course_dict = saved_state.get("course_dict")
            if saved_state.get("course_info") is not None:
                self.course_info = saved_state.get("course_info")
            if saved_state.get("chapter_info") is not None:
                self.chapter_info = saved_state.get("chapter_info")

    def save_state(self) -> dict:
        return {
            "version": VERSION_NAME,
            "cookies": self.agent.get_cookie_str(),
            "uid": self.uid,
            "course_dict": self.course_dict,
            "course_info": self.course_info,
            "chapter_info": self.chapter_info,
        }

    def get_agent(self) -> MyAgent:
        return self.agent

    def sign_in(self, uname: str, password: str):
        url = "https://passport2.chaoxing.com/fanyalogin"
        data = "fid=314&uname={0}&password={1}&refer=http%3A%2F%2Fi.chaoxing.com&t=true&forbidotherlogin=0".format(
            uname, base64.b64encode(password.encode("utf-8")).decode("utf-8"))
        headers = self.agent.build_headers_based_on({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie': 'fanyamoocs=11401F839C536D9E; fid=314; isfyportal=1; ptrmooc=t',
            'Host': 'passport2.chaoxing.com',
            'Origin': 'https://passport2.chaoxing.com',
            'Referer': 'https://passport2.chaoxing.com/login?loginType=4&fid=314&newversion=true&refer=http://i.mooc.chaoxing.com',
        }, self.agent.headers_additional_xhr)
        sign_in_rsp = requests.post(url=url, data=data, headers=headers)
        sign_in_json = sign_in_rsp.json()
        if sign_in_json["status"]:
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

    def url_302(self, oldUrl: str, additional_headers: dict = {}) -> str:
        headers = self.agent.build_headers_based_on(additional_headers)
        course_302_rsp = requests.get(
            url=oldUrl, headers=headers, allow_redirects=False)
        new_url = course_302_rsp.headers.get("Location")
        if new_url == None:
            new_url = oldUrl
        else:
            if G_VERBOSE:
                print("[INFO] 302 to " + new_url)
        if new_url == "https://mooc1.chaoxing.com/antispiderShowVerify.ac":
            raise MyError(0, G_STRINGS['antispider_verify'])
        return new_url

    def request(self, url: str, additional_headers: dict = {}, data=None, method="GET") -> requests.Response:
        headers = self.agent.build_headers_based_on(additional_headers)
        rsp = None
        if data != None:
            rsp = requests.request(
                method=method, url=url, headers=headers, data=data)
        else:
            rsp = requests.request(method=method, url=url, headers=headers)
        if rsp.status_code == 200:
            # print(rsp.text)
            for item in rsp.cookies:
                self.agent.update_cookie(item.name, item.value)
            return rsp
        else:
            raise MyError(rsp.status_code,
                          G_STRINGS['error_response'] + ": " + str(rsp.text))

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

    def load_courses(self) -> None:
        url = "https://mooc2-ans.chaoxing.com/visit/courses/list?v=" + \
            str(int(time.time() * 1000))

        course_html_text = self.request_xhr(url).text
        course_HTML = etree.HTML(course_html_text)

        list_in_html = course_HTML.xpath("//ul[@class='course-list']/li")
        if list_in_html.__len__() == 0:
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
        course_unit_list = chapters_HTML.xpath("//div[@class='chapter_unit']")
        for course_unit in course_unit_list:
            catalog_name = course_unit.xpath(
                "./div[@class='chapter_item']/div/div[@class='catalog_name']/span/@title")[0]
            print("# ", catalog_name)
            chapter_items = course_unit.xpath(
                "./div[@class='catalog_level']/ul/li/div[@class='chapter_item']")
            if chapter_items.__len__() == 0:
                if G_VERBOSE:
                    print(" * ", catalog_name, " is empty")
            for chapter_item in chapter_items:
                # parse chapter number
                chapter_number_str = chapter_item.xpath(
                    ".//span[@class='catalog_sbar']")[0].text.strip()

                # parse chapter title
                chapter_title: str
                chapter_title_node = chapter_item.xpath("./@title")
                if chapter_title_node.__len__() == 0:
                    chapter_title = chapter_item.xpath(
                        ".//div[@class='catalog_name']/text()")[1].strip()
                else:
                    chapter_title = chapter_title_node[0]

                # parse chapter link
                transfer_url: str = ""
                chapter_entrance_node = chapter_item.xpath("./@onclick")
                if chapter_entrance_node.__len__() == 0:
                    pass
                else:
                    chapter_entrance = chapter_entrance_node[0].strip()
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

                unfinished_count = 0
                task_status_HTML = chapter_item.xpath(
                    ".//div[@class='catalog_task']")[0]
                task_count_node: list = task_status_HTML.xpath(
                    "./input[@class='knowledgeJobCount']/@value")
                if task_count_node.__len__() == 1:
                    unfinished_count = int(task_count_node[0])

                chapter_info = {
                    'chepterNumber': chapter_number_str,
                    'chepterTitle': chapter_title,
                    'courseid': courseid,
                    'knowledgeId':  knowledgeId,
                    'clazzid': clazzid,
                    'transferUrl': transfer_url,
                    'unfinishedCount': unfinished_count,
                }
                chapter_list.append(chapter_info)

                print(" - {} {} [{}]".format(chapter_number_str,
                      chapter_title, knowledgeId))

        course_info['chapter_list'] = chapter_list
        self.course_info[courseid] = course_info
        print()
        return course_info

    def request_class_detail(self, course_id, clazz_id, course_cpi) -> dict:
        url = "https://mobilelearn.chaoxing.com/v2/apis/class/getClassDetail?fid=1606&courseId={}&classId={}".format(
            course_id, clazz_id)
        rsp_text = self.request(url, {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://mobilelearn.chaoxing.com/page/active/stuActiveList?courseid={}&clazzid={}&cpi={}&ut=s&fid=1606".format(course_id, clazz_id, course_cpi),
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }).text
        return json.loads(rsp_text)

    def get_chapters(self, index: int | str) -> list:
        index = str(index)
        course_name = self.course_dict[index][0]
        course_url = self.course_dict[index][1]

        parse_result = urllib.parse.urlparse(course_url)
        course_param = urllib.parse.parse_qs(parse_result.query)
        course_id = course_param.get("courseid")[0]
        clazz_id = course_param.get("clazzid")[0]
        course_cpi = course_param.get("cpi")[0]

        if G_VERBOSE:
            print("[INFO] get_chapters= [{}]{}".format(course_id, course_name))
            print(course_url)
            print()

        if self.course_info.__contains__(course_id) and G_CONFIG['always_request_course_info'] == False:
            return self.course_info[course_id]['chapter_list']
        else:
            return self.load_course_info(course_url)['chapter_list']

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
        #     "chepterNumber": "1.1",
        #     "chepterTitle": "第一课时",
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
            print("|{unfinishedCount}| {chepterNumber} {chepterTitle} {knowledgeId}".format(
                **chapter_meta))
            print(chapter_meta["transferUrl"])
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


class FxxkStarHelper():
    def __init__(self, fxxkstar: FxxkStar):
        self.fxxkstar = fxxkstar
        self.unfinished_chepters = []
        self.video_to_watch = []

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

        print(G_STRINGS['login_success'])

    def login_if_need(self) -> str:
        if self.fxxkstar.uid == -1:
            self.start_interactive_login(self.fxxkstar)
            time.sleep(2)
        return self.fxxkstar.uid

    def load_courses_if_need(self) -> dict:
        if self.fxxkstar.course_dict == {} or G_CONFIG['always_request_course_list']:
            self.fxxkstar.load_courses()
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
                    point_count, chapter['chepterNumber'], chapter['chepterTitle']))

        print("=" * 26)
        print()
        return unfinished_chapters

    def medias_deal(self, card_info: dict, course_id, clazz_id, chapter_id) -> None:
        card_args = card_info['card_args']
        card_url = card_info['card_url']
        attachments_json = card_args["attachments"]
        defaults_json = card_args["defaults"]

        course_id = defaults_json["courseid"] or course_id
        clazz_id = defaults_json["clazzId"] or clazz_id
        chapter_id = defaults_json["knowledgeid"] or chapter_id

        for attachment_item in attachments_json:
            attachment_type = attachment_item.get("type")

            if attachment_type == "document":
                mod = DocumentModule(self.fxxkstar, attachment_item,
                                     card_args, course_id, clazz_id, chapter_id)

            elif attachment_type == "live":
                mod = LiveModule(self.fxxkstar, attachment_item,
                                 card_args, course_id, clazz_id, chapter_id)

            elif attachment_type == "video":
                mod = VideoModule(self.fxxkstar, attachment_item,
                                  card_args, course_id, clazz_id, chapter_id)

                if mod.can_play():
                    self.video_to_watch.append(mod)

            elif attachment_type == "workid":
                mod = WorkModule(self.fxxkstar, attachment_item=attachment_item, card_args=card_args,
                                 course_id=course_id, clazz_id=clazz_id, chapter_id=chapter_id)

                with open(f"temp/work/work_{mod.work_id}.html", "w") as f:
                    f.write(mod.load())
                print("[Work] ", mod.title, mod.work_id, " saved")

                if not mod.is_approved:
                    questions = mod.parse_paper(mod.paper_html)
                    # mod.correct_answers(questions, mod.work_id, card_url)
                    if G_VERBOSE:
                        print(questions)
                    # mod.upload_answers(questions)

            else:
                print("attachment_item", attachment_item)

    def deal_chapter(self, chapter_meta: dict) -> None:
        chapter_info = self.fxxkstar.load_chapter(chapter_meta)
        for num in range(chapter_info['card_count']):
            time.sleep(random.random() * 2)
            card_info = chapter_info['cards'][num]
            self.medias_deal(
                card_info, chapter_meta['courseid'], chapter_meta['clazzid'], chapter_meta['knowledgeId'])

    def get_cookies(self) -> str:
        return self.fxxkstar.get_agent().get_cookie_str()

    def sync_video_progress(self) -> None:
        video_report_thread_pool = []
        while self.video_to_watch:
            video_item: VideoModule = self.video_to_watch.pop(0)
            video_report_thread_pool.append(video_report_thread(video_item))
        print(G_STRINGS['sync_video_progress_started'])
        for item in video_report_thread_pool:
            item.start()
            time.sleep(1)
        for item in video_report_thread_pool:
            item.join()
        print(G_STRINGS['sync_video_progress_ended'])
        print()


class AttachmentModule:
    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_args: dict, course_id, clazz_id, chapter_id):
        self.fxxkstar = fxxkstar
        self.uid = fxxkstar.uid
        self.attachment_item = attachment_item
        self.card_args = card_args
        self.course_id = course_id
        self.clazz_id = clazz_id
        self.chapter_id = chapter_id
        self.mid = attachment_item['mid']
        self.defaults = card_args['defaults']
        self.no_job = attachment_item.get("job") == None
        self.module_type = attachment_item.get("type")
        self.attachment_property = attachment_item.get("property")


class LiveModule(AttachmentModule):
    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_args: dict, course_id, clazz_id, chapter_id):
        super().__init__(fxxkstar, attachment_item,
                         card_args, course_id, clazz_id, chapter_id)

        assert self.module_type == "live"

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
        if self.live_info['temp'].__contains__('data') and self.live_info['temp']['data'].__contains__['mp4Url']:
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

        def setLiveANDCourseRelation(self) -> dict:
            relation_url = "https://mooc1.chaoxing.com" + \
                f"/ananas/live/relation?courseid={course_id}&knowledgeid={chapter_id}&ut=s&jobid={job_id}&aid={a_id}"
            resp1 = fxxkstar.request_xhr(relation_url, {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": "https://mooc1.chaoxing.com/ananas/modules/live/index.html?v=2022-0324-1900"
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
                "Referer": "https://mooc1.chaoxing.com/ananas/modules/live/index.html?v=2022-0324-1900"
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
                "Referer": "https://mooc1.chaoxing.com/ananas/modules/live/index.html?v=2022-0324-1900"
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
        live_status = info_data["liveStatus"]
        if_review = info_data["ifReview"]
        if live_status == 0:
            return 'liveUnplayed'
        elif live_status == 1:
            return 'liveLiving'
        elif live_status == 4 and if_review == 1:
            return 'liveFinished'
        elif live_status == 4 and if_review == 0:
            return 'livePlayback'


class DocumentModule(AttachmentModule):
    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_args: dict, course_id, clazz_id, chapter_id):
        super().__init__(fxxkstar, attachment_item,
                         card_args, course_id, clazz_id, chapter_id)
        assert self.module_type == "document"

        self.other_info = attachment_item.get("otherInfo")
        self.jtoken = attachment_item.get("jtoken")
        self.name = self.attachment_property.get("name")
        self.object_id = self.attachment_property.get("objectid")

        print("[DocumentModule] ", self.name)
        self.status_data = DocumentModule._request_status(
            self.fxxkstar, self.object_id)
        print("[DocumentModule] ", self.status_data['pdf'])

        if not self.no_job:
            jobid = attachment_item.get("jobid")
            DocumentModule._misson_doucument(fxxkstar=self.fxxkstar, course_id=course_id,
                                             clazz_id=clazz_id, chapter_id=chapter_id, jobid=jobid, jtoken=self.jtoken)

    @staticmethod
    def _request_status(fxxkstar: FxxkStar, object_id: str) -> dict:
        assert len(object_id) > 1
        status_url = "https://mooc1.chaoxing.com/ananas/status/{}?flag=normal&_dc={}".format(
            object_id, int(time.time() * 1000))
        status_rsp = fxxkstar.request_xhr(status_url, {
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/pdf/index.html?v=2022-0218-1135"
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
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/pdf/index.html?v=2022-0218-1135"
        }, method="GET")
        print("[INFO] mission_document")
        print(multimedia_rsp.text)
        print()


class VideoModule(AttachmentModule):
    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_args: dict, course_id, clazz_id, chapter_id):
        super().__init__(fxxkstar, attachment_item,
                         card_args, course_id, clazz_id, chapter_id)
        assert self.module_type == "video"

        self.object_id = attachment_item.get("objectId")
        self.other_info = attachment_item.get("otherInfo")
        self.jobid = attachment_item.get("jobid")
        self.name = self.attachment_property.get("name")

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
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/video/index.html?v=2022-0324-1800"
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

    def gen_report_url(self, playing_time) -> str | None:
        if not self.can_play():
            return None

        duration = self.status_data.get('duration')
        dtoken = self.status_data.get('dtoken')
        report_url_base = self.defaults['reportUrl']
        if G_VERBOSE:
            print("video._gen_report_url", self.object_id, self.other_info,
                  self.jobid, self.uid, self.name, duration, report_url_base)
            print()

        report_enc = VideoModule.encode_enc(
            self.clazz_id, int(duration), self.object_id, self.other_info, self.jobid, self.uid, str(playing_time))
        other_args = "/{0}?clazzId={1}&playingTime={2}&duration={3}&clipTime=0_{3}&objectId={4}&otherInfo={5}&jobid={6}&userid={7}&isdrag=0&view=pc&enc={8}&rt=0.9&dtype=Video&_t={9}".format(
            dtoken, self.clazz_id, playing_time, duration, self.object_id, self.other_info, self.jobid, self.uid, report_enc, int(time.time() * 1000))
        report_url_result = report_url_base + other_args

        return report_url_result

    @staticmethod
    def encode_enc(clazzid: str, duration: int, objectId: str, otherinfo: str, jobid: str, userid: str, currentTimeSec: str):
        import hashlib
        data = "[{0}][{1}][{2}][{3}][{4}][{5}][{6}][0_{7}]".format(clazzid, userid, jobid, objectId, int(
            currentTimeSec) * 1000, "d_yHJ!$pdA~5", duration * 1000, duration)
        if G_VERBOSE:
            print("[INFO] encode_enc=" + data)
        return hashlib.md5(data.encode()).hexdigest()


class WorkModule(AttachmentModule):
    # module/work/index.html?v=2021-0927-1700
    def __init__(self, fxxkstar: FxxkStar, attachment_item: dict, card_args: dict, course_id, clazz_id, chapter_id):
        super().__init__(fxxkstar, attachment_item,
                         card_args, course_id, clazz_id, chapter_id)
        assert self.module_type == "workid"

        self.work_id = self.attachment_property['workid']
        self.jobid = self.attachment_property['jobid']
        self.title = self.attachment_property['title']
        print("[WorkModule] ", self.title, self.work_id)

    def load(self):
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

        headers = self.fxxkstar.agent.build_headers_based_on(self.fxxkstar.agent.headers_additional_iframe, {
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/work/index.html?v=2021-0927-1700&castscreen=0"
        })
        src2 = self.fxxkstar.url_302(src, headers)
        src3 = self.fxxkstar.url_302(src2, headers)
        work_HTML_text = self.fxxkstar.request(src3, headers).text
        if G_VERBOSE:
            print()
        self.is_approved = "selectWorkQuestionYiPiYue" in src3
        self.paper_html = work_HTML_text
        return work_HTML_text

    @staticmethod
    def parse_paper(paper_page_html: str) -> List[dict]:
        "Parsing the questions and answers in the page html into dict"
        soup = BeautifulSoup(paper_page_html, "lxml")
        form1 = soup.find("form", id="form1")
        question_divs = form1.find_all("div", class_="TiMu")
        title_tags = ["【单选题】", "【多选题】", "【填空题】", "【判断题】"]
        questions = []
        for question_div in question_divs:
            question_title = question_div.select(
                ".Zy_TItle > .clearfix,.Cy_TItle > .clearfix")[0].text.strip()
            for title_tag in title_tags:
                if question_title.startswith(title_tag):
                    question_title = question_title[len(title_tag):].strip()
                    break
            answertype_node = question_div.find(
                "input", id=re.compile("answertype"))
            question_type = int(answertype_node.get("value"))
            question_id = answertype_node.get("id")[10:]
            question = {
                "topic": question_title,
                "type": question_type,
                "question_id": question_id,
            }
            if question_type == 0 or question_type == 1:
                options = []
                selected = []
                option_nodes = question_div.select("ul.fl li")
                for option_node in option_nodes:
                    option_input_node = option_node.select(
                        "label.fl.before input")[0]
                    option = option_input_node.get("value")
                    content = option_node.select("a.fl.after")[0].text.strip()
                    option_info = {"option": option, "content": content}
                    options.append(option_info)
                    if option_input_node.get("checked") == "true":
                        selected.append(option_info)
                question['options'] = options
                if selected.__len__() > 0:
                    question['answers'] = selected
            elif question_type == 3:
                choices_node = question_div.find_all(
                    "input", attrs={"name": f"answer{question_id}"})
                selected = []
                for choice_node in choices_node:
                    if choice_node.get("checked") == "true":
                        judge = choice_node.get("value")
                        if judge == "true":
                            selected.append({"option": True, "content": True})
                        elif judge == "false":
                            selected.append(
                                {"option": False, "content": False})
                        else:
                            selected.append(
                                {"option": judge, "content": judge})
                        break
                if len(selected) > 0:
                    question['answers'] = selected
            elif question_type == 2:
                content = question_div.find(
                    attrs={"name": f"answer{question_id}"}).get("value")
                if content:
                    question['answers'] = [{"option": "一", "content": content}]
            else:
                print("not support question type:", question_type)
            questions.append(question)
        return questions

    @staticmethod
    def render_paper(paper_page_html: str, questions_state: List[dict]) -> str:
        "Render the answers in question dict to the page html"
        soup = BeautifulSoup(paper_page_html, "lxml")
        form1 = soup.find("form", id="form1")
        for question in questions_state:
            q_type: int = question['type']
            q_id = question['question_id']
            q_topic = question['topic']
            answers = question['answers']
            if q_type == 0:  # single choice
                answer_option = answers[0]['option']
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
                answer_judgment = answers[0]['option']
                for option_node in form1.find_all(attrs={"name": f"answer{q_id}"}):
                    if str(option_node['value']).lower() == str(answer_judgment).lower():
                        option_node['checked'] = "true"
                    else:
                        del option_node['checked']
            elif q_type == 2:  # fill in the blank
                option_node = form1.find_all(attrs={"name": f"answer{q_id}"})
                option_node['value'] = answers[0]['content']
            else:
                print("not support question type:", q_type)
        return soup.decode()

    @staticmethod
    def chaoxing_type_to_banktype(chaoxing_type: int) -> int:
        "Convert the question type of chaoxing to the type of answerbank"
        # 0: Single Choice, 1: Multiple Choice, 2: Fill in the Blank, 3: Judgment | chaoxing
        # 1: Single Choice, 2: Multiple Choice, 3: Judgment, 4: Fill in the Blank | answerbank
        translate_map = {
            0: 1,
            1: 2,
            2: 4,
            3: 3
        }
        return translate_map[chaoxing_type]

    @staticmethod
    def banktype_to_chaoxing_type(banktype: int) -> int:
        "Convert the question type of answerbank to the type of chaoxing"
        translate_map = {
            1: 0,
            2: 1,
            4: 2,
            3: 3
        }
        return translate_map[banktype]

    @staticmethod
    def random_answer(question_state: dict) -> dict:
        "Randomly generate the answers in the question dict"
        question = question_state.copy()
        q_type = question['type']
        options = question['options']
        answer = []
        if q_type == 0:
            answer.append(random.choice(options))
        elif q_type == 1:
            for option in options:
                if random.random() > 0.5:
                    answer.append(option)
        elif q_type == 2:
            answer.append({"option": "一", "content": ""})
        elif q_type == 3:
            answer.append(random.choice(options))
        question['answers'] = answer
        return question

    @staticmethod
    def fix_answers_option(question: dict) -> None:
        "Regenerate the answer according to the options of the question"
        if question['type'] not in [0, 1]:
            return
        options = question['options']
        answers = question['answers']
        new_answers = []
        for option in options:
            for answer in answers:
                if option['content'] == answer['content']:
                    new_answers.append(option)
                    break
        question['answers'] = new_answers

    @staticmethod
    def module_work_submit(fxxkstar: FxxkStar, work_page_html: str) -> bool:
        soup = BeautifulSoup(work_page_html, "lxml")
        form1 = soup.find("form", id="form1")
        course_id = soup.find(id="courseId").get("value")
        class_id = soup.find(id="classId").get("value")
        enc_work = soup.find(id="enc_work").get("value")
        total_question_num = soup.find(id="totalQuestionNum").get("value")

        parms = FxxkStar.extract_form_fields(form1)
        answer_all_id = ""
        for key in parms:
            if key.startswith("answertype"):
                answer_all_id += key[10:] + ","
        parms['answerwqbid'] = answer_all_id
        parms['pyFlag'] = "1"

        ajax_url = "https://mooc1.chaoxing.com" + \
            f"/work/addStudentWorkNew?_classId={class_id}&courseid={course_id}&token={enc_work}&totalQuestionNum={total_question_num}"
        ajax_type = form1.get("method") or "post"
        ajax_data = urllib.parse.urlencode(parms)
        ajax_url += f"&ua={fxxkstar.get_client_type()}"
        ajax_url += f"&formType={ajax_type}"
        ajax_url += "&saveStatus=1"
        ajax_url += "&version=1"

        rsp_text = fxxkstar.request_xhr(ajax_url, {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://mooc1.chaoxing.com/ananas/modules/work/index.html?v=2021-0927-1700&castscreen=0",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }, data=ajax_data, method=ajax_type).text
        # {"msg":"保存成功！","status":true}
        if G_VERBOSE:
            print("[INFO] module_work_submit, rsp_text=" + rsp_text)
        result = json.loads(rsp_text)
        if result['status'] == True:
            print(result['msg'])
            return True
        else:
            raise MyError(result['msg'] + " " + rsp_text)

    def upload_answers(self, answers: List[dict]) -> None:
        answered_html = WorkModule.render_paper(self.paper_html, answers)
        WorkModule.module_work_submit(self.fxxkstar, answered_html)


class video_report_thread(threading.Thread):

    def __init__(self, video_mod: VideoModule):
        super(video_report_thread, self).__init__()
        self.multimedia_headers = video_mod.fxxkstar.agent.build_headers_based_on(
            video_mod.fxxkstar.agent.headers_additional_xhr, {
                'Accept': '*/*',
                'Content-Type': 'application/json',
                'Referer': 'https://mooc1.chaoxing.com/ananas/modules/video/index.html?v=2022-0324-1800',
            })
        self.clazz_id = video_mod.clazz_id
        self.duration = video_mod.status_data['duration']
        self.jobid = video_mod.jobid
        self.object_id = video_mod.object_id
        self.other_info = video_mod.other_info
        self.uid = video_mod.uid
        self.total_time = int(self.duration)
        self.video_mod = video_mod

    def run(self) -> None:
        rsp = requests.get(url=self.video_mod.gen_report_url(
            0), headers=self.multimedia_headers)
        print("[video_thread]", rsp.status_code)
        cookieTmp = self.multimedia_headers['Cookie']
        for item in rsp.cookies:
            cookieTmp = cookieTmp + '; ' + item.name + '=' + item.value
        self.multimedia_headers.update({"Cookie": cookieTmp})
        print("[%s] 0/%d" % (self.name, self.total_time))
        time_now = 60
        while time_now < self.total_time + 60:
            time.sleep(60)
            rsp = requests.get(url=self.video_mod.gen_report_url(
                time_now), headers=self.multimedia_headers)
            print("[%s] %d/%d" %
                  (self.name, time_now, self.total_time))
            if G_VERBOSE:
                print(self.name, rsp.text)
            time_now = time_now + 60

        rsp = requests.get(url=self.video_mod.gen_report_url(
            self.total_time), headers=self.multimedia_headers)
        print("[%s] %s" % (self.name, rsp.text))


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
    print()


def read_state_from_file() -> dict:
    saved_file = open('star.json', 'rb')
    saved_data = json.loads(saved_file.read())
    saved_file.close()
    return saved_data


def save_state_to_file(fxxkstar: FxxkStar) -> None:
    save_file = open('star.json', 'w', encoding='utf-8')
    save_file.write(json.dumps(fxxkstar.save_state(), ensure_ascii=False))
    save_file.close()
    print(G_STRINGS['save_state_success'])


def prepare() -> FxxkStar:
    agent = MyAgent(G_HEADERS)

    fxxkstar = None
    try:
        saved_data = read_state_from_file()
        fxxkstar = FxxkStar(agent, saved_data)
    except FileNotFoundError:
        fxxkstar = FxxkStar(agent)

    return fxxkstar


if __name__ == "__main__":
    before_start()
    fxxkstar = None
    try:
        fxxkstar = prepare()

        helper = FxxkStarHelper(fxxkstar)
        helper.login_if_need()
        helper.load_courses_if_need()
        helper.print_course_list()

        choose_course = input(G_STRINGS['input_course_num'])
        print()
        chapters = fxxkstar.get_chapters(choose_course)
        time.sleep(2)

        unfinished_chapters = helper.select_unfinished_chapters(chapters)
        time.sleep(2)

        while True:
            choose_chapter = input(G_STRINGS['input_chapter_num'])
            choose_chapter = int(choose_chapter) - 1
            print()
            if 0 <= choose_chapter < unfinished_chapters.__len__():
                helper.deal_chapter(unfinished_chapters[choose_chapter])
                print()
            else:
                break

        if input(G_STRINGS['input_if_sync_video_progress']) == 'y':
            helper.sync_video_progress()

    except Exception as err:
        tag = "[{}] ".format(time.asctime(time.localtime(time.time())))
        print(tag, traceback.format_exc())
        print(err)
        if G_CONFIG['save_state'] and fxxkstar is not None:
            save_state_to_file(fxxkstar)
        input()
    finally:
        if G_CONFIG['save_state'] and fxxkstar is not None:
            save_state_to_file(fxxkstar)
