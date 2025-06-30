import os
import time
from typing import Any, List, Dict, Tuple

from app.core.config import settings
from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType
from app.utils.http import RequestUtils

import re
from urllib.parse import unquote

class Esb(_PluginBase):
    # 插件名称
    plugin_name = "Esb"
    # 插件描述
    plugin_desc = "消息桥梁服务，信息转发至其他服务。"
    # 插件图标
    plugin_icon = "Chatgpt_A.png"
    # 插件版本
    plugin_version = "0.2.1"
    # 插件作者
    plugin_author = "songYu"
    # 作者主页
    author_url = "https://github.com/amber1888"
    # 插件配置项ID前缀
    plugin_config_prefix = "esb_"
    # 加载顺序
    plugin_order = 15
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    openai = None
    _enabled = False

    song_yu_url = None
    max_retry = 5
    download_path = "/manhua"

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self.song_yu_url = config.get("song_yu_url")
            self.max_retry = 5
            self.download_path = config.get("download_path")


    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'song_yu_url',
                                            'label': 'song yu server',
                                            'placeholder': 'https://100.18.2.1:8000',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'download_path',
                                            'label': '漫画下载路径',
                                            'placeholder': '/manhua',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '开启插件后，消息交互时使用请[问帮你]开头，或者以？号结尾，或者超过10个汉字/单词，则会触发ChatGPT回复。'
                                                    '开启辅助识别后，内置识别功能无法正常识别种子/文件名称时，将使用ChatGTP进行AI辅助识别，可以提升动漫等非规范命名的识别成功率。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "song_yu_url": "",
            "download_path": "",
        }

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(EventType.UserMessage)
    def talk(self, event: Event):
        if not self._enabled:
            return None
        text = event.event_data.get("text")
        userid = event.event_data.get("userid")
        channel = event.event_data.get("channel")
        logger.info(f"接收用户消息: {text}")
        if not text:
            return None
        # 必须esb开头
        if not text.startswith("jm"):
            return None
        text = text.replace("jm", "").replace("jm ", "")

        if "tag" not in text:
            logger.info(f"接收禁漫号: {text}。开始调用下载器")
            data = {
                "passwd": 0,
                "pdf": True,
                "Titletype": 1
            }

            for i in range(self.max_retry):
                try:
                    res = RequestUtils(
                        timeout=10
                    ).get_res(
                        url=f'{self.song_yu_url}/get_pdf/' + str(text),
                        params=data
                    )
                    logger.info(f"返回:{res}")
                    logger.info(type(res))
                    if res:
                        if res.status_code == 200:
                            file_name = self.parse_content_disposition(res.headers["Content-Disposition"])
                            local_filename = os.path.join(self.download_path, file_name)
                            logger.info(f"文件下载路径：{local_filename}")
                            with open(local_filename, "wb") as f:
                                for chunk in res.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            self.post_message(channel=channel, title="请求下载成功", userid=userid)
                            return True
                    self.post_message(channel=channel, title=f'第{i}次下载失败，重试中......', userid=userid)
                    time.sleep(2)
                except Exception as e:
                    logger.error(e)
        else:
            text = text.replace("tag", "").split()
            logger.info(f"开始搜索tag: {text}")
            page = 1
            if ":" in text:
                inputs = text.split(":")
                data = {"query": str(inputs[0]), "page": int(inputs[1])}
            else:
                data = {"query": str(text), "page": page}
            logger.info("请求参数: %s" % data)

            res = RequestUtils(
                timeout=10
            ).get_res(
                url=f'{self.song_yu_url}/search',
                params=data
            )
            try:
                if res:
                    if res.status_code == 200:
                        ret_json = res.json()
                        response = ""
                        for album in ret_json["data"]["results"]:
                            response += "%s:%s\n" % (album["id"], album["title"])
                        self.post_message(channel=channel, title=response, userid=userid)
                        return True
                return None
            except Exception as e:
                logger.error(e)
                return None

    def parse_content_disposition(self, header):
        # 提取 filename（标准字段）和 filename*（RFC 5987编码字段）
        filename_match = re.search(r'filename="([^"]+)"', header)
        filename_star_match = re.search(r'filename\*=(?:UTF-8\'\'|)([^\s;]+)', header, re.IGNORECASE)

        # 优先使用RFC 5987编码的filename*
        if filename_star_match:
            encoded = filename_star_match.group(1)
            return unquote(encoded, encoding='utf-8')

        # 次选：标准filename字段
        if filename_match:
            return filename_match.group(1)

        # 否则按时间戳命名
        return time.time()

    def stop_service(self):
        """
        退出插件
        """
        pass
