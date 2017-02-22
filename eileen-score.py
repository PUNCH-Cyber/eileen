#!/usr/bin/python
import requests
from os.path import expanduser
import yaml
import json
import sys
import re
from datetime import datetime, timedelta
import glob, os
from collections import Counter

today_date = datetime.now().strftime("%Y-%m-%d")
print "Running on", today_date
config_file = expanduser("~") + '/.bigtime/eileen-config'
config = yaml.safe_load(open(config_file))

logdir = expanduser("~") + '/.bigtime/log/'

days_of_week = ['Monday','Tuesday','Wednesday',
    'Thursday','Friday','Saturday','Sunday']

employee_score = Counter()
employee_days = Counter()
for logfilename in glob.glob(logdir + "timecard-data-*.json"):
    print(logfilename)
    with open(logfilename, 'r') as logfile:
        timecard_data = json.load(logfile)
    logdate = re.sub(logdir + "timecard-data-", '', logfilename)
    logdate = re.sub("\.json",'', logdate)
    print logdate
    #print timecard_data
    employees = {}
    try:
        tc_data = timecard_data['Data']
        for record in tc_data:
            name = record[4]
            date = record[9]
            if name in employees.keys():
                if date not in employees[name]:
                    employees[name].append(date)
            else:
                employees[name] = [date]
        dayobj = datetime.strptime(logdate, "%Y-%m-%d") - timedelta(days=1)
        day = dayobj.strftime("%Y-%m-%d")
        dow = datetime.strptime(day, "%Y-%m-%d").weekday()
        if dow > 4: # don't show results for weekend days
            continue
        for name in employees.keys():
            if name not in config['ignore']:
                employee_days[name] += 1
                if day in employees[name]:
                    employee_score[name] += 1
    except KeyError:
        print "Bad data in ", logfilename
        pass

report = ""
report_dow = datetime.strptime(today_date, "%Y-%m-%d").weekday()
report += "Timecard Compliance Scores as of "
report += today_date + " " + days_of_week[report_dow] + "\n"
employee_names_to_report = employee_days.keys()
employee_names_to_report.sort()
for employee in employee_names_to_report:
    report +=  employee + " " + \
        str((employee_score[employee] / float(employee_days[employee])) * 100) \
        + "%\n"
print "Slack report: \n" + report

slack_payload = {
    "text":report,
    "channel": config['channel'],
    "icon_emoji": config['emoji'],
    "username": config['username']
    }

'''
if report != "":
    print "sending to slack...", slack_payload
    r = requests.post(config['slack_webhook_url'],
        data = json.dumps(slack_payload))
    print "slack response:", r.text
else:
    print "Nothing to report"
'''
