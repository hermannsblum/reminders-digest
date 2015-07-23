#!/usr/bin/python
# -*- coding: utf-8 -*-

import caldav
import icalendar
import urllib
import datetime as dt
import json
import locale

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import smtplib


config = json.loads(open('settings.json', 'r').read())

client = caldav.DAVClient(config['caldav']['url'],
                          username=config['caldav']['username'],
                          password=config['caldav']['password'],
                          ssl_verify_cert=False)
# insert when working: '/usr/share/ca-certificates/server.crt'
principal = client.principal()
calendars = principal.calendars()
overdue = []
today = []
working_on = []
for calendar in calendars:
    for todo in calendar.todos():
        ics = icalendar.Calendar.from_ical(todo.data)
        for component in ics.walk():
            due = component.get('due')
            metadata = component.get('X-2DOAPP-METADATA')

            if component.name == 'VTODO' and due is not None:
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
            if component.name == 'VTODO' and metadata is not None:
                metadata = metadata.replace('<2Do Meta>', '')
                metadata = metadata.replace('</2Do Meta>', '')
                decoded = json.loads(urllib.unquote(metadata).decode('utf8'))
                if 'StartDate' in decoded.keys():
                    startdate = dt.datetime.fromtimestamp(int(decoded['StartDate'])).date()
                    if startdate <= dt.date.today():
                        working_on.append({'title': component.get('summary'),
                                        'date': startdate})

locale.setlocale(locale.LC_ALL, 'de_DE')
date_format = '%a %d. %b'
datetime_format = '%a %d. %b %H:%M'
mail_text = "Überfällig\n----------\n"
html_text = "<strong>Überfällig</strong><br>"
for item in overdue:
    format = date_format
    if item['time']:
        format = datetime_format
    mail_text = mail_text + "{}: {}\n".format(item['title'].encode('utf-8'), item['date'].strftime(format))
    html_text = html_text + "{}: {}<br>".format(item['title'].encode('utf-8'), item['date'].strftime(format))
mail_text = mail_text + "\nHeute\n-----\n"
html_text = html_text + "<br><strong>Heute</strong><br>"
for item in today:
    format = date_format
    if item['time']:
        format = datetime_format
    mail_text = mail_text + "{}: {}\n".format(item['title'].encode('utf-8'), item['date'].strftime(format))
    html_text = html_text + "{}: {}<br>".format(item['title'].encode('utf-8'), item['date'].strftime(format))
mail_text = mail_text + "\nIn Arbeit\n---------\n"
html_text = html_text + "<br><strong>In Arbeit</strong><br>"
for item in working_on:
    mail_text = mail_text + "{}: {}\n".format(item['title'].encode('utf-8'), item['date'].strftime(date_format))
    html_text = html_text + "{}: {}<br>".format(item['title'].encode('utf-8'), item['date'].strftime(date_format))

fromaddr = "Server"
toaddr = config['mail']['recipient']
msg = MIMEMultipart('alternative')
msg['From'] = fromaddr
msg['To'] = toaddr
msg['Subject'] = "Was gibt es Heute zu tun?"
msg.attach(MIMEText(mail_text, 'plain', 'UTF-8'))
msg.attach(MIMEText(html_text, 'html', 'UTF-8'))

server = smtplib.SMTP(config['mail']['smtp'], config['mail']['port'])
server.ehlo()
server.starttls()
server.ehlo()
server.login(str(config['mail']['username']), str(config['mail']['password']))

text = msg.as_string()
server.sendmail(fromaddr, toaddr, text)
