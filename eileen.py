#!/usr/bin/python3.6
import requests
from os.path import expanduser
import yaml
import json
import sys
from datetime import datetime, timedelta


def create_bigtime_session(user, password):
    """
    Establish bigtime session and return session header

    """
    session_url = 'https://iq.bigtime.net/BigtimeData/api/v2/session'
    payload = {"UserId": user, "Pwd": password}
    r = requests.post(session_url, params = payload)
    r.raise_for_status()
    session = json.loads(r.text)
    session_headers = {'user-agent': 'DMC Robot v1.0',
                       'X-Auth-Token': session['token'],
                       'X-Auth-Realm': session['firm'] }
    return session_headers

def GET_endpoint(url, session_headers):
    r = requests.get(url, headers = session_headers)
    r.raise_for_status()
    return json.loads(r.text)

def POST_endpoint(url, session_headers, data):
    r = requests.post(url, headers = session_headers, data = data)
    r.raise_for_status()
    return json.loads(r.text)

def POST_slack(webhook_url, content):
    print("Sending to slack...", content)
    r = requests.post(webhook_url, data = json.dumps(content))
    print("Slack response:", r.text)


if __name__ == '__main__':
    date = datetime.now().strftime("%Y-%m-%d")
    print("Running on", date)

    credentials_file = expanduser("~") + '/.bigtime/credentials'
    credentials = yaml.safe_load(open(credentials_file))
    config_file = expanduser("~") + '/.bigtime/eileen-config'
    config = yaml.safe_load(open(config_file))
    logfilename = expanduser("~") + '/.bigtime/log/timecard-data-' + date + '.json'

    # Payload for failed events
    failure_payload = {
        "text": "A failure has occurred",
        "channel": config['channel'],
        "icon_emoji": config['emoji'],
        "username": config['username']
    }

    # generate the ISO date strings for the range of days we care about
    days_to_go_back = 1
    dates_obj = [datetime.today() - timedelta(days=x) for x in \
        range(1,days_to_go_back + 1)]
    dates = [x.strftime("%Y-%m-%d") for x in dates_obj]
    days_of_week = ['Monday','Tuesday','Wednesday', 'Thursday','Friday','Saturday','Sunday']

    employees = {}

    try:
        session_headers = create_bigtime_session(credentials['UserId'], credentials['Pwd'])
    except requests.exceptions.HTTPError:
        POST_slack(config['slack_webhook_url'], failure_payload)
        sys.exit(1)

    # Gather personnel roster report
    personnel_roster_url = config.get('personnel_roster_url', None)
    if personnel_roster_url is not None:

        try:
            response = GET_endpoint(personnel_roster_url, session_headers)
        except requests.exceptions.HTTPError:
            POST_slack(config['slack_webhook_url'], failure_payload)
            sys.exit(1)

        for entry in response['Data']:
            employee_name = entry[1]
            employees[employee_name] = []

    # Gather timesheet detail report for API consumption
    try:
        data = {'DT_BEGIN': dates[0], 'DT_END': dates[-1]}
        response = POST_endpoint(config['timesheet_report_url'], session_headers, data)
    except requests.exceptions.HTTPError:
        POST_slack(config['slack_webhook_url'], failure_payload)
        sys.exit(1)

    with open(logfilename, 'w') as logfile:
        json.dump(response, logfile)

    for record in response['Data']:
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

    # Gather A/R aging detail report
    aging_report_url = config.get('aging_report_url', None)
    if aging_report_url is not None:
        aged_projects = {}

        try:
            response = GET_endpoint(aging_report_url, session_headers)
        except requests.exceptions.HTTPError as error:
            POST_slack(config['slack_webhook_url'], failure_payload)
            sys.exit(1)

        for entry in response['Data']:
            age = entry[1]
            project = entry[2]
            invoice_date = entry[4]
            invoice_number = entry[6]
            amount = entry[8]
            balance = entry[10]

            if (age < 365) and balance:
                if age not in aged_projects:
                    aged_projects[age] = []
                aged_projects[age].append([project, invoice_date, invoice_number, '$' + str(balance)])

        for key in sorted(aged_projects.keys()):
            report += '\nProjects aged @ {} days with an outstanding balance\n'.format(key)
            for entry in aged_projects[key]:
                report += '\t {}\n'.format(' - '.join(entry))

    print(report)

    success_payload = {
        "text":report,
        "channel": config['channel'],
        "icon_emoji": config['emoji'],
        "username": config['username']
        }

    if report != "":
        POST_slack(config['slack_webhook_url'], success_payload)
    else:
        print("Nothing to report")

# EOF
