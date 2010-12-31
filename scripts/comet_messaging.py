#!/usr/bin/python
# example based on http://thomas.pelletier.im/2010/08/websocket-tornado-redis/

"""
how to use this?

1) install tornado

   easy_install tornado

2) start this app:

   python scripts/comet_messaging.py -k mykey -p 8888

3) from a web2py app you can post messages with

   from scripts.comet_messaging import comet_send
   comet_send('http://127.0.0.1:8888','Hello World','mykey')

4) from views you can receive them with

   <script>
   $(document).ready(function(){
      web2py_comet('ws://127.0.0.1:8888/realtime/',function(e){alert(e.data)});
   });
   </script>

When the server posts a message, all clients connected to the page will popup an alert message

"""

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import hmac
import sys
import optparse
import urlib

listeners = {}

def comet_send(url,message,hmac_key=None):
    sig = hmac_key and hmac.new(hmac_key,message).hexdigest() or ''
    params = urllib.urlencode({'message': message, 'signature': sig})
    f = urllib.urlopen(url, params)
    data= f.read()
    f.close()
    return data

class PostHandler(tornado.web.RequestHandler):
    def post(self):
        if hmac_key and not 'signature' in self.request.arguments: return 'false'
        if 'message' in self.request.arguments:
            print pessage
            message = self.request.arguments['message'][0]
            group = self.request.arguments.get('group',['default'])[0]           
            if hmac_key:
                signature = self.request.arguments['signature'][0]
                if not hmac.new(hmac_key,message).hexdigest()==signature: return 'false'
            for client in listeners[group]: client.write_message(message)
            return 'true'
        return 'false'

class DistributeHandler(tornado.websocket.WebSocketHandler):
    def open(self):        
        self.group = self.request.arguments.get('group',['default'])[0]
        if not self.group in listeners: listeners[self.group]=[]
        listeners[self.group].append(self)
        print 'client connected via websocket'
    def on_message(self, message):
        pass
    def on_close(self):
        if self.group in listeners: listeners[self.group].remove(self)
        print 'client disconnected'

if __name__ == "__main__":
    usage = "comet_messaging -p 8888 -k <hmac_key>"
    version= ""
    parser = optparse.OptionParser(usage, None, optparse.Option, version)
    parser.add_option('-p',
                      '--port',
                      default='8888',
                      dest='port',
                      help='socket')
    parser.add_option('-k',
                      '--hmac_key',
                      default='',
                      dest='hmac_key',
                      help='hmac_key')
    (options, args) = parser.parse_args()
    hmac_key = options.hmac_key
    urls=[
        (r'/', PostHandler),
        (r'/realtime/', DistributeHandler)]
    application = tornado.web.Application(urls, auto_reload=True)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(int(options.port))
    tornado.ioloop.IOLoop.instance().start()
