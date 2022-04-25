# FxxkStar

[![Python 3.10](https://img.shields.io/badge/python-v3.10-blue)](https://www.python.org/) [![License](https://img.shields.io/github/license/chettoy/FxxkStar)](https://raw.githubusercontent.com/chettoy/FxxkStar/main/LICENSE) ![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/chettoy/FxxkStar)

`FxxkStar` is an *API* and *example unofficial client* for the *SuperStar* online classroom platform (or *chaoxing*; *xuexitong*), that provides a better learning experience for students. 

- Are you still struggling because of the user experience of the official client and web version?
- Do you want to use your favorite player to watch videos and browse documents so that you can take some notes in split screen or download them for later viewing without worrying about not having a study record?
- Do you want to get the correct answer immediately after answering the post-lesson questions to save time in finding the correct answer?

**API Features:**

- [x] Login and access to course information

- [x] Get a list of chapters

- [x] Get video and document links

- [x] Get after-class questions

- [x] Synchronize video playback progress

- [x] Get message notifications


**CLI Client Features:**

- [x] Interactive login and listing of course
- [x] Show the list of chapters and the chapters with incomplete tasks
- [x] Show download links for documents and live replay
- [x] Synchronize video playback progress
- [x] Quick view of after-class questions
- [ ] Interactive question answering (not implemented)
- [ ] Check-in reminders and message reminders (not implemented)



## Screenshots

![Screenshot](https://github.com/chettoy/FxxkStar/raw/main/images/screenshot1.png)
![Screenshot](https://github.com/chettoy/FxxkStar/raw/main/images/screenshot2.png)



## Installation

You can download FxxkStar by cloning the [Git](https://github.com/chettoy/FxxkStar) repository:

```shell
git clone --depth 1 https://github.com/chettoy/FxxkStar.git FxxkStar-dev
```

FxxkStar works with [Python](https://www.python.org/download/) version 3.10 or above on any platform.

**requirements**

- `lxml`, `beautifulsoup4`, `requests`, `zstandard`

You can install requirements with the following command (using TUNA mirror):

```shell
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple lxml
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple beautifulsoup4
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple zstandard
```



## Contributing

We'd love to have your helping hand on `FxxkStar`! 



## Acknowledgments
- [https://github.com/liuyunfz/chaoxing_tool](https://github.com/liuyunfz/chaoxing_tool)
- [https://github.com/CodFrm/cxmooc-tools](https://github.com/CodFrm/cxmooc-tools)
- [https://github.com/chettoy/FxxkSsxx](https://github.com/chettoy/FxxkSsxx)



## License

```
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
```

