import sys, socket, select, threading, ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

TARGET_HOST = None
LISTEN_PORT = 8088

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if path.startswith('/stream/'):
            self._handle_stream(path)
        elif path.startswith('/proxy/'):
            self._handle_proxy(path)
        else:
            self.send_error(404)
    
    def _handle_stream(self, path):
        channel = path.split('/stream/', 1)[1]
        self.send_response(200)
        self.send_header('Content-Type', 'audio/x-mpegurl')
        self.end_headers()
        self.wfile.write(b'#EXTM3U\n')
        self.wfile.write(f'#EXTINF:-1,{channel}\n'.encode())
        self.wfile.write(f'# Relay placeholder\n'.encode())
    
    def _handle_proxy(self, path):
        target_url = path.split('/proxy/', 1)[1]
        self.log_message(f'Proxying: {target_url[:100]}')
        import urllib.request
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(target_url)
            req.add_header('User-Agent', 'okhttp/4.9.0')
            req.add_header('Accept', '*/*')
            req.add_header('Accept-Language', 'en')
            req.add_header('X-Requested-With', 'XMLHttpRequest')
            resp = urllib.request.urlopen(req, context=ctx, timeout=30)
            data = resp.read()
            self.send_response(resp.status)
            ct = resp.headers.get('Content-Type', 'application/octet-stream')
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(f'HTTP {e.code}'.encode())
        except Exception as e:
            self.send_error(502, str(e))
    
    def do_CONNECT(self):
        host, _, port_str = self.path.partition(':')
        port = int(port_str) if port_str else 443
        self.log_message(f'CONNECT {host}:{port}')
        try:
            sock = socket.create_connection((host, port), timeout=15)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ssock = ctx.wrap_socket(sock, server_hostname=host)
            self.send_response(200, 'Connection Established')
            self.end_headers()
            self._relay(self.connection, ssock)
        except Exception as e:
            self.log_message(f'CONNECT error: {e}')
            self.send_error(502, str(e))
    
    def _relay(self, client, remote):
        client.setblocking(0)
        remote.setblocking(0)
        sockets = [client, remote]
        try:
            while True:
                readable, _, exceptional = select.select(sockets, [], sockets, 30)
                if not readable and not exceptional:
                    break
                for s in readable:
                    data = s.recv(8192)
                    if not data:
                        return
                    if s is client:
                        remote.sendall(data)
                    else:
                        client.sendall(data)
                for s in exceptional:
                    return
        except:
            pass
        finally:
            for s in sockets:
                try:
                    s.close()
                except:
                    pass
    
    def log_message(self, format, *args):
        sys.stderr.write('[%s] %s\n' % (threading.current_thread().name, format % args))

def run_proxy():
    server = HTTPServer(('0.0.0.0', LISTEN_PORT), ProxyHandler)
    print(f'Phone relay listening on 0.0.0.0:{LISTEN_PORT}')
    print(f'Use: adb forward tcp:{LISTEN_PORT} tcp:{LISTEN_PORT}')
    print(f'Then configure Kodi proxy to localhost:{LISTEN_PORT}')
    server.serve_forever()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        LISTEN_PORT = int(sys.argv[1])
    run_proxy()
