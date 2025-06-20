import json
from typing import Any, List, Dict, Tuple

from app.core.config import settings
from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType
from app.utils.http import RequestUtils


class Esb(_PluginBase):
    # 插件名称
    plugin_name = "Esb"
    # 插件描述
    plugin_desc = "消息桥梁服务，信息转发至其他服务。"
    # 插件图标
    plugin_icon = "Chatgpt_A.png"
    # 插件版本
    plugin_version = "0.0.4"
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

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")

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
            "enabled": False
        }

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(EventType.UserMessage)
    def talk(self, event: Event):
        if not self._enabled:
            return
        text = event.event_data.get("text")
        userid = event.event_data.get("userid")
        channel = event.event_data.get("channel")
        logger.info(f"接收用户消息: {text}")
        if not text:
            return
        # 必须esb开头
        if not text.startswith("jm"):
            return
        text = text.replace("jm", "").replace("jm ", "")

        if "?" not in text:
            logger.info(f"接收禁漫号: {text}。开始调用下载器")
            data = {"album_id": str(text)}
            res = RequestUtils(
                timeout=10,
                content_type="application/json"
            ).post_res(
                url='http://192.168.1.96:18000/download-album',
                json=data
            )
        else:
            text = text.replace("?", "")
            logger.info(f"开始搜索tag: {text}")
            data = {"tag": str(text)}
            res = RequestUtils(
                timeout=10,
                content_type="application/json"
            ).post_res(
                url='http://192.168.1.96:18000/query-album',
                json=data
            )
        logger.info(f"<UNK>: {res}")
        try:
            if res:
                ret_json = res.json()
                response = ""
                for album in ret_json["result"]:
                    response += "%s:%s\n" % (album["album_id"], album["title"].encode('utf-8').decode('unicode_escape'))
                logger.info(f"返回：{response}")
                self.post_message(channel=channel, title=response, userid=userid)
        except Exception as e:
            logger.error(e)

    def stop_service(self):
        """
        退出插件
        """
        pass
