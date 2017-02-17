#!/usr/bin/python
import requests
from os.path import expanduser
import yaml
import json
import sys
from datetime import datetime, timedelta

date = datetime.now().strftime("%Y-%m-%d")
print "Running on", date

credentials_file = expanduser("~") + '/.bigtime/credentials'
credentials = yaml.safe_load(open(credentials_file))
config_file = expanduser("~") + '/.bigtime/eileen-config'
config = yaml.safe_load(open(config_file))
logfilename = expanduser("~") + '/.bigtime/log/timecard-data-' + date + '.json'


# generate the ISO date strings for the range of days we care about
days_to_go_back = 1
dates_obj = [datetime.today() - timedelta(days=x) for x in \
    range(1,days_to_go_back + 1)]
dates = [x.strftime("%Y-%m-%d") for x in dates_obj]
days_of_week = ['Monday','Tuesday','Wednesday',
    'Thursday','Friday','Saturday','Sunday']

# func to quit and spit out an error if we get a negative response from the api
def exit_on_fail(status_code, response_text):
    if status_code != 200:
        print "ERROR, exiting..."
        print "HTTP_CODE:", status_code
        print "RESPONSE:", response_text
        slack_payload = {
            "text": "I failed!",
            "channel": config['channel'],
            "icon_emoji": config['emoji'],
            "username": config['username']
            }
        r = requests.post(config['slack_webhook_url'],
            data = json.dumps(slack_payload))
        print "slack response:", r.text
        sys.exit(1)

# establish session and get tokens
session_url = 'https://iq.bigtime.net/BigtimeData/api/v2/session'
payload = {"UserId": credentials['UserId'], "Pwd": credentials['Pwd']}
r = requests.post(session_url, params = payload)
exit_on_fail(r.status_code, r.text)
session = json.loads(r.text)
session_headers = { 'user-agent': 'DMC Robot v1.0',
    'X-Auth-Token': session['token'], 'X-Auth-Realm': session['firm'] }

# Timesheet detail report for API consumption
r = requests.get(config['timesheet_report_url'], headers = session_headers)
exit_on_fail(r.status_code, r.text)
timecard_data = json.loads(r.text)

with open(logfilename, 'w') as logfile:
    json.dump(timecard_data, logfile)

employees = {}
for record in timecard_data['Data']:
    name = record[4]
    date = record[9]
    if name in employees.keys():
        if date not in employees[name]:
            employees[name].append(date)
    else:
        employees[name] = [date]

report = ""
for day in dates:
    dow = datetime.strptime(day, "%Y-%m-%d").weekday()
    if dow > 4: # don't show results for weekend days
        continue
    report += day + " " + days_of_week[dow] + "\n"
    for name in employees.keys():
        if name not in config['ignore']:
            if day in employees[name]:
                report += '\t' + name + " - Great work! :grinning:\n"
            else:
                report += '\t' + name + \
                    " - Please complete your timecard! :rage:\n"

print report

slack_payload = {
    "text":report,
    "channel": config['channel'],
    "icon_emoji": config['emoji'],
    "username": config['username']
    }

if report != "":
    print "sending to slack...", slack_payload
    r = requests.post(config['slack_webhook_url'],
        data = json.dumps(slack_payload))
    print "slack response:", r.text
else:
    print "Nothing to report"


























# EOF
