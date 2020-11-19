from flask import Flask, request, redirect, url_for, send_file, send_from_directory
import time
import threading
import os
import subprocess
import socket
import json

def create_dir(name):
    if not os.path.exists(name):
        os.makedirs(name)
create_dir('wavs')
create_dir('queryResult')
create_dir('query')
create_dir('tmp')

app = Flask(__name__, static_url_path='')
UPLOAD_FOLDER = 'query'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
queryCount = 0
threadrunning = [False] * 2

class QueryThread(threading.Thread):
    def __init__(self, task_id, thread_id):
        super(QueryThread, self).__init__()
        self.task_id = task_id
        self.thread_id = thread_id
    def run(self):
        try:
            wav_file = os.path.join('wavs', self.task_id + '.wav')
            result_file = os.path.join('queryResult', self.task_id + '.out')
            ffmpeg_log = 'ffmpeg_t'+str(self.thread_id)+'.log'
            tmp_out = os.path.join('tmp', 'tmp_t'+str(self.thread_id)+'.out')
            subprocess.run(['ffmpeg',
                '-i', os.path.join(app.config['UPLOAD_FOLDER'], self.task_id + '.flac'),
                '-y', wav_file
            ], stderr=open(ffmpeg_log, 'a'))
            sock = socket.socket()
            sock.connect(('127.0.0.1', 1605))
            sock.send(('query ' + wav_file + '\n').encode('utf-8'))
            nread = 0
            with open(tmp_out, 'wb') as fout:
                while True:
                    buf = sock.recv(1024)
                    nread += len(buf)
                    fout.write(buf)
                    if len(buf) == -1:
                        crash = True
                    if len(buf) < 1024:
                        break
                if nread == 0:
                    fout.write(json.dumps({'progress':'error','reason':'server crashed'}))
            os.rename(tmp_out, result_file)
        except ConnectionRefusedError as x:
            with open(result_file, 'w') as fout:
                fout.write(json.dumps({'progress':'error','reason':'server unavailable'}))
            raise
        except ConnectionResetError as x:
            with open(result_file, 'w') as fout:
                fout.write(json.dumps({'progress':'error','reason':'server crashed'}))
            raise
        except Exception as x:
            with open(result_file, 'w') as fout:
                fout.write(json.dumps({'progress':'error','reason':'unknown'}))
            raise
        finally:
            threadrunning[self.thread_id] = False

@app.route('/')
def index_page():
    return send_file('public/index.html')

@app.route('/js/<path:filename>')
def js_files(filename):
    return send_from_directory('public/js', filename)

@app.route('/libflac.min.wasm.js')
def libflac():
    return send_file('public/libflac.min.wasm.js')

@app.route('/libflac.min.wasm.wasm')
def libflac_wasm():
    return send_file('public/libflac.min.wasm.wasm')

@app.route('/css/<path:filename>')
def css_files(filename):
    return send_from_directory('public/css', filename)

@app.route('/audio/<path:filename>')
def audio_files(filename):
    return send_from_directory('public/audio', filename)

@app.route('/query', methods=['POST'])
def query():
    global queryCount
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    genname = time.strftime('%Y-%m-%dT%H-%M-%S') + '_' + str(queryCount)
    tid = None
    for i in range(len(threadrunning)):
        if not threadrunning[i]:
            tid = i
    if tid is not None:
        queryCount += 1
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], genname + '.flac'))
        async_task = QueryThread(genname, tid)
        threadrunning[tid] = True
        async_task.start()
        return genname
    else:
        return 'too many requests', 429

@app.route('/queryResult/<path>')
def queryResult(path):
    response = send_from_directory('queryResult', path + '.out')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

if __name__ == "__main__":
    app.run(port=5025, debug=False)
