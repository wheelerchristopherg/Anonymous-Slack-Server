#!/usr/bin/python3

from flask import *
import requests
import threading
import queue
import re
import os

app = Flask(__name__)

debug = False
webhook = ""

if 'ANON_DEBUG' in os.environ and os.environ['ANON_DEBUG'].lower() == 'true':
    debug = True

if 'ANON_WEBHOOK' in os.environ:
    webhook = os.environ['ANON_WEBHOOK']
else:
    print("no webhook; define ANON_WEBHOOK environment variable")
    exit()

dms = "C09ELN6LC" #replace with a private message channel id or a dev channel id

debug_channel = dms if debug else ""

message_queue = queue.Queue()

def send_message():
    block = False
    global_emoji_count = 0
    while True:
        if block:
            global_emoji_count -= 1

        if global_emoji_count <= 0:
            global_emoji_count = 0
            block = False

        message = message_queue.get()
		
        if 'debug' in message:
            body = {"username":message['username'],"icon_url":message['icon_url'],"text":message['text'],"channel":dms}
            req = requests.post(webhook, data=json.dumps(body), headers={"content-type":"application/json"})
            continue

        if '!here' in message['text'] or '!everyone' in message['text'] or '<@' in message['text']:
            if message['response_url'] != "":
                body = {'response_type':'ephemeral', 'text':'@here, @channel, and individual pings are disabled for /anon'}
                req = requests.post(message['response_url'], data=json.dumps(body), headers={"content-type":"application/json"})
            continue

        colon_count = 0
        local_emoji_count = 0
        for c in message['text']:
            if c == ':':
                colon_count += 1
            if colon_count == 2:
                colon_count = 0
                local_emoji_count += 1
                if not block:
                    global_emoji_count += 1

        if block and local_emoji_count > 0:
            if message['response_url'] != "":
                body = {"response_type":"ephemeral", "text":"too many emotes have been used recently, stop it"}
                req = requests.post(message['response_url'], data=json.dumps(body), headers={"content-type":"application/json"})
        elif (not block) and local_emoji_count >= 5:
            if message['response_url'] != "":
                body = {"response_type":"ephemeral", "text":"woah, slow down there, too many emojis"}
                req = requests.post(message['response_url'], data=json.dumps(body), headers={"content-type":"application/json"})
            global_emoji_count -= local_emoji_count
        elif message['text'] != "":
            body = {"username":message['username'],"icon_url":message['icon_url'],"text":message['text'],"channel":debug_channel}
            req = requests.post(webhook, data=json.dumps(body), headers={"content-type":"application/json"})
            if local_emoji_count == 0:
                global_emoji_count -= 1
        if global_emoji_count > 30:
            block = True

        message_queue.task_done()
            

@app.route('/json', methods=['POST'])
def recieve_json():
	text = request.json["text"]
	message_queue.put({"text": request.json['text'],"icon_url": request.json['icon_url'], "username":request.json['username'], "response_url":""})
	return "", 200, {'ContentType':'application/json'} 

@app.route('/form', methods=['POST'])
def recieve_form():
    response_url = request.form.get("response_url", "", type=str)
    icon_url = request.form.get("icon_url", "https://www.shareicon.net/data/512x512/2015/09/17/102476_anonymous_512x512.png", type=str)
    username = request.form.get("username", "anon", type=str)
    message_queue.put({"text": request.form['text'],"icon_url": icon_url, "username":username, "response_url":response_url})
    return "", 200, {'ContentType':'application/json'} 

@app.route('/test', methods=['POST'])
def recieve_test():
    icon_url = request.form.get("icon_url", "https://www.shareicon.net/data/512x512/2015/09/17/102476_anonymous_512x512.png", type=str)
    username = request.form.get("username", "anon", type=str)
    message_queue.put({"text": request.form['text'],"icon_url": icon_url, "username":username, "debug":""})

    return "", 200, {'content-type':'application/json'}

if __name__ == '__main__':
    print("Debug mode: {0}".format(debug))
    t = threading.Thread(target=send_message, daemon=True)
    t.start()
    del t
    app.run(host="0.0.0.0",port="2000")
