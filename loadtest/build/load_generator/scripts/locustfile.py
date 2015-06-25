import logging
import gevent
import pprint
import os
import json
import flask
import jinja2
import time
from flask import Flask, Response, render_template, send_from_directory, send_file
from gevent.queue import Queue
from locust import HttpLocust, TaskSet, task, events, web

influx_queue = Queue(100000)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
my_loader = jinja2.ChoiceLoader([
    jinja2.FileSystemLoader(os.path.join(PROJECT_ROOT, 'templates')),
    web.app.jinja_loader,
])
web.app.jinja_loader = my_loader

def get_requests_per_second(stat, client_id):
    request = stat['method'] + stat['name'].replace('/', '-')
    request_key = "locust.{0}.reqs_per_sec.{1}".format(request, client_id)

    for epoch_time, count in stat['num_reqs_per_sec'].items():
      influx_queue.put( {'request_key':request_key, 'requests_per_second':count, 'epoch_time':epoch_time} )

def slave_report_log (client_id, data, ** kw):
  print(data)
  for stat in data['stats']:
    get_requests_per_second(stat, client_id)

class JsonSerialization(TaskSet):
  @task(1)
  def json(self):
    with self.client.get("/", catch_response=True) as response:
      logging.debug('Response headers:')
      logging.debug(pprint.pformat(response.headers, 2))
      logging.debug('Response content:')
      logging.debug(response.content)    

class WebsiteUser(HttpLocust):
  task_set = JsonSerialization

# Server sent events
class ServerSentEvent:
    FIELDS = ('event', 'data', 'id')
    def __init__(self, data, event=None, event_id=None):
        self.data = data
        self.event = event 
        self.id = event_id 

    def encode(self):
        if not self.data:
            return ""
        ret = []
        for field in self.FIELDS:
            entry = getattr(self, field) 
            if entry is not None:
                ret.extend(["%s: %s" % (field, line) for line in entry.split("\n")])
        return "\n".join(ret) + "\n\n"

@web.app.route("/dashboard")
def my_dashboard():
    return render_template('dashboard.html')

@web.app.route("/files/<path:path>")
def send_js(path):
    return send_file(PROJECT_ROOT + '/files/' + path)

@web.app.route("/stream")
def stream():
    def gen():
        while True:
            if influx_queue.empty():
              time.sleep(0.05)
              continue
            queue_data = influx_queue.get()
            data = json.dumps({"slave_id": queue_data['request_key'], 'rps': queue_data['requests_per_second'], 'epoch': queue_data['epoch_time']})
            ev = ServerSentEvent(data)
            yield ev.encode()
            time.sleep(0.05)

    return Response(gen(), mimetype="text/event-stream")

events.slave_report += slave_report_log
