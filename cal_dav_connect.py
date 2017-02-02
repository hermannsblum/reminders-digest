#!/usr/bin/python
# -*- coding: utf-8 -*-

import caldav
import icalendar
import urllib
import datetime as dt
import json
import locale

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


def get_calendar_data(config):
    client = caldav.DAVClient(config['caldav']['url'],
                              username=config['caldav']['username'],
                              password=config['caldav']['password'],
                              ssl_verify_cert=True)
    # insert when working: '/usr/share/ca-certificates/server.crt'
    principal = client.principal()
    calendars = principal.calendars()
    overdue = []
    today = []
    working_on = []
    for calendar in calendars:
        try:
            todos = calendar.todos()
        except AttributeError as e:
            # do noting
            todos = []
        for todo in todos:
            ics = icalendar.Calendar.from_ical(todo.data)
            for component in ics.walk():
                if component.name != 'VTODO':
                    # is not a todo
                    continue

                if component.get('completed') is not None:
                    # task is completed
                    continue

                due = component.get('due')
                metadata = component.get('X-2DOAPP-METADATA')

                if due is not None:
                    time = False
                    if type(due.dt) is dt.date:
                        due_date = due.dt
                    else:
                        due_date = due.dt.date()
                        time = True
                    if due_date < dt.date.today():
                        overdue.append({'title': component.get('summary'),
                                        'date': due.dt,
                                        'time': time})
                        continue
                    if due_date == dt.date.today():
                        today.append({'title': component.get('summary'),
                                      'date': due.dt,
                                      'time': time})
                if metadata is not None:
                    metadata = metadata.replace('<2Do Meta>', '')
                    metadata = metadata.replace('</2Do Meta>', '')
                    decoded = json.loads(urllib.unquote(metadata).decode('utf8'))
                    if 'StartDate' in decoded.keys():
                        startdate = dt.datetime.fromtimestamp(int(decoded['StartDate'])).date()
                        if startdate <= dt.date.today():
                            working_on.append({'title': component.get('summary'),
                                            'date': startdate})
    return overdue, today, working_on


def format_todo_item(item, format):
    # return "{}: {}".format(item['title'].encode('utf-8'), item['date'].strftime(format))
    return "{}: {}".format(item['title'], item['date'].strftime(format))


def build_text(overdue, today, working_on):
    locale.setlocale(locale.LC_ALL, 'de_DE')
    date_format = '%a %d. %b'
    datetime_format = '%a %d. %b %H:%M'
    mail_text = "Überfällig\n----------\n"
    for item in overdue:
        format = date_format
        if item['time']:
            format = datetime_format
        mail_text = mail_text + format_todo_item(item, format) + "\n"
    mail_text = mail_text + "\nHeute\n-----\n"
    for item in today:
        format = date_format
        if item['time']:
            format = datetime_format
        mail_text = mail_text + format_todo_item(item, format) + "\n"
    mail_text = mail_text + "\nIn Arbeit\n---------\n"
    for item in working_on:
        mail_text = mail_text + format_todo_item(item, format) + "\n"
    return mail_text


def build_html(overdue, today, working_on):
    locale.setlocale(locale.LC_ALL, 'de_DE')
    date_format = '%a %d. %b'
    datetime_format = '%a %d. %b %H:%M'
    html_text = "<strong>Überfällig</strong><br>"
    for item in overdue:
        format = date_format
        if item['time']:
            format = datetime_format
        html_text = html_text + format_todo_item(item, format) + "<br>"
    html_text = html_text + "<br><strong>Heute</strong><br>"
    for item in today:
        format = date_format
        if item['time']:
            format = datetime_format
        html_text = html_text + format_todo_item(item, format) + "<br>"
    html_text = html_text + "<br><strong>In Arbeit</strong><br>"
    for item in working_on:
        html_text = html_text + format_todo_item(item, format) + "<br>"
    return html_text


def send_mail(config, text, html):
    fromaddr = "Server"
    toaddr = config['mail']['recipient']
    msg = MIMEMultipart('alternative')
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Was gibt es Heute zu tun?"
    msg.attach(MIMEText(text, 'plain', 'UTF-8'))
    msg.attach(MIMEText(html, 'html', 'UTF-8'))

    server = smtplib.SMTP(config['mail']['smtp'], config['mail']['port'])
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(str(config['mail']['username']), str(config['mail']['password']))

    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.close()

if __name__ == '__main__':
    config = json.loads(open('settings.json', 'r').read())
    todos = get_calendar_data(config)
    plain_text = build_text(todos[0], todos[1], todos[2])
    html_text = build_html(todos[0], todos[1], todos[2])
    send_mail(config, plain_text, html_text)
