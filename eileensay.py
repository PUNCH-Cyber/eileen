#!/usr/bin/python
import requests
from os.path import expanduser
import yaml
import json
import sys
from datetime import datetime, timedelta

date = datetime.now().strftime("%Y-%m-%d")
print "Running on", date

config_file = expanduser("~") + '/.bigtime/eileen-config'
config = yaml.safe_load(open(config_file))

channel = sys.argv[1]
report = sys.argv[2]

slack_payload = {
    "text":report,
    "channel": channel,
    "icon_emoji": config['emoji'],
    "username": config['username']
    }

if report != "":
    r = requests.post(config['slack_webhook_url'],
        data = json.dumps(slack_payload))
    print "slack response:", r.text
else:
    print "Nothing to report"


























# EOF
