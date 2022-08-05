import subprocess

subprocess.run(["bash", "run.sh"])

import os
import secrets

from flask import Flask, render_template, request, session
from flask.helpers import url_for

from src.backbone import load_bot

debug = False

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"

model = load_bot(
    df_context_path="./datasets/clusterdf_context.csv",
    df_uttr_path="./datasets/clusterdf_uttr.csv",
    model_name="cl-tohoku/bert-base-japanese",
    tsne_context_path="./datasets/tsne_context.pkl",
    tsne_uttr_path="./datasets/tsne_uttr.pkl",
    max_length=32,
    threshold=0.7,
)


@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == "static":
        filename = values.get("filename", None)
        if filename:
            file_path = os.path.join(app.root_path, endpoint, filename)
            values["q"] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


@app.route("/")
def home():
    id_ = secrets.token_urlsafe(16)
    model.register_chat_id(id_)
    session.update({"id": id_})
    return render_template("index.html")


@app.route("/message", methods=["POST"])
def message():
    id_ = session.get("id")
    data = request.get_data()
    data = data.decode("utf-8").split(";")

    context = " [SEP] ".join(data[-2:])
    reply = model.reply(context, id_)
    print(reply)
    return {"context": context, "reply": reply, "history": data}


if __name__ == "__main__":
    if debug:
        app.run(debug=debug)
    else:
        app.run(host="0.0.0.0", debug=debug)
