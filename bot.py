import os
import pickle
import random
import re
import time
from typing import List, NoReturn

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from openTSNE import TSNE
from telegram import message
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)
from telegram.update import Update

# BERT-Japanese
from transformers import AutoConfig, AutoModel, AutoTokenizer

from src.backbone import Filter, ReplyBot, load_bot
from src.utils import read_config_file

try:
    CONFIG: dict = read_config_file(".telegram")
except:
    CONFIG: dict = {
        "TOKEN": os.environ.get("TOKEN"),
        "DIALOGUE_LENGTH": int(os.environ.get("DIALOGUE_LENGTH")),
    }


class YuBot:
    def __init__(self) -> None:
        self.config = CONFIG
        self.user_context: dict = {}
        self.backbone = load_bot(
            df_context_path="./datasets/clusterdf_context.csv",
            df_uttr_path="./datasets/clusterdf_uttr.csv",
            model_name="cl-tohoku/bert-base-japanese",
            tsne_context_path="./datasets/tsne_context.pkl",
            tsne_uttr_path="./datasets/tsne_uttr.pkl",
            max_length=32,
            threshold=0.7,
        )
        self._validate_config()

    def _validate_config(self) -> NoReturn:
        if not getattr(self, "config"):
            raise ValueError
        if not (
            "TOKEN" in self.config.keys() and "DIALOGUE_LENGTH" in self.config.keys()
        ):
            raise ValueError
        if not (
            isinstance(self.config["TOKEN"], str)
            and isinstance(self.config["DIALOGUE_LENGTH"], int)
        ):
            raise ValueError

    def start(self, update: Update, context: CallbackContext) -> NoReturn:
        # 対話ログと発話回数を初期化
        self.user_context[update.message.from_user.id] = {
            "context": ["湯川先輩，お疲れ様です!!😄"],
            "count": 1,
        }
        self.backbone.register_chat_id(update.message.from_user.id)

        # システムからの最初の発話
        # 以下の発話に限定しません．任意の発話を返してください
        update.message.reply_text("湯川先輩，お疲れ様です!!😄")

    def _reply(self, context: str, id: int):
        response = self.backbone.reply(context, id=id, show_candidate=False)
        return response

    def message(self, update: Update, context: CallbackContext):
        if update.message.from_user.id not in self.user_context:
            self.user_context[update.message.from_user.id] = {
                "context": ["湯川先輩，お疲れ様です!!😄"],
                "count": 1,
            }

        # ユーザ発話の回数を更新 && Turnを保持
        self.user_context[update.message.from_user.id]["count"] += 1

        # ユーザ発話をcontextに追加
        user_message = update.message.text
        self.user_context[update.message.from_user.id]["context"].append(user_message)

        # replyメソッドによりcontextから発話を生成
        msg_context = " [SEP] ".join(
            self.user_context[update.message.from_user.id]["context"][-2:]
        )
        if self.user_context[update.message.from_user.id]["count"] == 1:
            send_message = "次の週末にオンライン飲み会をやろうと思うんですが、先輩もどうですか！？"
        else:
            send_message = self._reply(msg_context, id=update.message.from_user.id)

        # 送信する発話をcontextに追加
        self.user_context[update.message.from_user.id]["context"].append(send_message)

        update.message.reply_text(send_message)

        if (
            self.user_context[update.message.from_user.id]["count"]
            >= self.config["DIALOGUE_LENGTH"]
        ):
            # 対話IDは unixtime:user_id:bot_username
            unique_id = (
                str(int(time.mktime(update.message["date"].timetuple())))
                + ":"
                + str(update.message.from_user.id)
                + ":"
                + context.bot.username
            )

            update.message.reply_text("_FINISHED_:" + unique_id)
            update.message.reply_text(
                "対話終了です．エクスポートした「messages.html」ファイルを，フォームからアップロードしてください．"
            )

    def run(self) -> NoReturn:
        updater = Updater(self.config["TOKEN"], use_context=True)

        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", self.start))

        dp.add_handler(MessageHandler(Filters.text, self.message))

        updater.start_polling()

        updater.idle()


if __name__ == "__main__":
    bot = YuBot()
    bot.run()
