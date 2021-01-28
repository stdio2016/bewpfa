from flask import Flask, request, redirect, url_for, send_file, send_from_directory, render_template
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

result_lock = threading.Lock()
past_query_lock = threading.Lock()
query_names = os.listdir('queryResult')
query_names.sort()
query_results = []
for name in query_names:
    if name.endswith('.out'):
        with open(os.path.join('queryResult', name), 'r', encoding='utf8') as fin:
            name = name[:-4]
            d = {'name': name}
            try:
                dat = json.load(fin)
                if dat['progress'] == 100:
                    top1 = dat['songs'][0]
                    d = {**d, 'result': top1['name']}
                else:
                    d = {**d, 'result': 'error'}
            except Exception as x:
                print('error %s! %s' % (x, name))
                d = {**d, 'result': 'parse error!'}
            query_results.append(d)

def write_status(path, data):
    if type(data) == str:
        is_bin = 'w'
    else:
        is_bin = 'wb'
    with result_lock, open(path, is_bin) as fout:
        fout.write(data)

class QueryThread(threading.Thread):
    def __init__(self, task_id, thread_id, query_type):
        super(QueryThread, self).__init__()
        self.task_id = task_id
        self.thread_id = thread_id
        self.query_type = query_type
    def run(self):
        try:
            wav_file = os.path.join('wavs', self.task_id + '.wav')
            result_file = os.path.join('queryResult', self.task_id + '.out')
            ext = '.flac' if self.query_type == 'recording' else ''
            ffmpeg_log = 'ffmpeg_t'+str(self.thread_id)+'.log'
            subprocess.run(['ffmpeg',
                '-i', os.path.join(app.config['UPLOAD_FOLDER'], self.task_id + ext),
                '-y', wav_file
            ], stderr=open(ffmpeg_log, 'a'))
            write_status(result_file, json.dumps({'progress':50}))
            sock = socket.socket()
            sock.connect(('127.0.0.1', 1605))
            sock.send(('query ' + wav_file + '\n').encode('utf-8'))
            nread = 0
            result = []
            while True:
                buf = sock.recv(1024)
                nread += len(buf)
                result.append(buf)
                if len(buf) < 1024:
                    break
            result = b''.join(result)
            if nread == 0:
                write_status(result_file, json.dumps({'progress':'error','reason':'server crashed'}))
            else:
                dat = json.loads(result.decode('utf8'))
                if 'songs' in dat and len(dat['songs']) > 0:
                    top1 = dat['songs'][0]
                    d = {'name': self.task_id, 'result': top1['name']}
                else:
                    d = {'name': self.task_id, 'result': 'error'}
                with past_query_lock:
                    query_results.append(d)
                write_status(result_file, result)
        except ConnectionRefusedError as x:
            write_status(result_file, json.dumps({'progress':'error','reason':'server unavailable'}))
            raise
        except ConnectionResetError as x:
            write_status(result_file, json.dumps({'progress':'error','reason':'server crashed'}))
            raise
        except Exception as x:
            write_status(result_file, json.dumps({'progress':'error','reason':'unknown'}))
            raise
        finally:
            threadrunning[self.thread_id] = False

@app.route('/<filename>')
def all_files(filename):
    return send_from_directory('public', filename)

@app.route('/')
def index_page():
    return send_file('public/index.html')

@app.route('/js/<path:filename>')
def js_files(filename):
    return send_from_directory('public/js', filename)

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
    querytype = request.form.get('querytype', 'recording')
    genname = time.strftime('%Y-%m-%dT%H-%M-%S') + '_' + str(queryCount)
    if querytype == 'recording':
        ext = '.flac'
    elif querytype == 'upload':
        ext = ''
    else:
        return 'Unknown query type', 400
    tid = None
    for i in range(len(threadrunning)):
        if not threadrunning[i]:
            tid = i
    if tid is not None:
        queryCount += 1
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], genname + ext))
        async_task = QueryThread(genname, tid, querytype)
        threadrunning[tid] = True
        async_task.start()
        result_file = os.path.join('queryResult', genname + '.out')
        write_status(result_file, json.dumps({'progress':0}))
        return genname
    else:
        return 'too many requests', 429

@app.route('/queryResult/<path>')
def queryResult(path):
    with result_lock:
        response = send_from_directory('queryResult', path + '.out')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

@app.route('/wavs/<path>')
def wav_files(path):
    response = send_from_directory('wavs', path)
    return response

@app.route('/pastQueries')
def past_queries():
    with past_query_lock:
        return render_template('pastQueries.html', query_results=query_results)

if __name__ == "__main__":
    app.run(port=5025, debug=False)
