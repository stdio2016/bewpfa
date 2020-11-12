from flask import Flask, request, redirect, url_for, send_file, send_from_directory
import time
import threading
import os
import subprocess

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
            subprocess.run(['ffmpeg',
                '-i', os.path.join(app.config['UPLOAD_FOLDER'], self.task_id + '.flac'),
                '-y', os.path.join('wavs', self.task_id + '.wav')
            ], stderr=open('q'+str(self.thread_id)+'.log', 'a'))
            with open(os.path.join('queryResult', self.task_id + '.out'), 'w') as fout:
                fout.write('{"progress":100,"songs":[{"name":"00001.mp3","score":100}]}')
        except Exception as x:
            with open(os.path.join('queryResult', self.task_id + '.out'), 'w') as fout:
                fout.write('{"progress":"error"}')
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
        with open(os.path.join('queryResult', genname + '.out'), 'w') as fout:
            fout.write('{"progress":0}')
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
