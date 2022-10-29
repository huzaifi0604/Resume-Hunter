from flask import *
from flask_socketio import SocketIO, emit, disconnect
from threading import Lock, Event
import os
import docx
import PyPDF2

async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = '5dec1cfe7c0c2ec55c17fb44b43f7d14'
socket_ = SocketIO(app, async_mode=async_mode)

parseThread = None
parse_thread_lock = Lock()

event= Event()

def Naive(text, match):
    for i in range(len(text)-len(match)+1):
        j=0
        while j<len(text):
            if text[j]!=match[i+j]:
                break
            j+=1
        if j==len(text):
            return True
    return False

def rabinKarp(text, match, q=101, d=256):
    M = len(text)
    N = len(match)
    i = 0
    j = 0
    p = 0
    t = 0 
    h = 1
 
    for i in range(M-1):
        h = (h*d) % q
 
    for i in range(M):
        p = (d*p + ord(text[i])) % q
        t = (d*t + ord(match[i])) % q
 
    for i in range(N-M+1):
        if p == t:
            for j in range(M):
                if match[i+j] != text[j]:
                    break
                else:
                    j += 1
 
            if j == M:
                return True

        if i < N-M:
            t = (d*(t-ord(match[i])*h) + ord(match[i+M])) % q

            if t < 0:
                t = t+q
    return False

def computeLPSArray(pat, M, lps):
    len = 0 
 
    lps[0]
    i = 1

    while i < M:
        if pat[i]== pat[len]:
            len += 1
            lps[i] = len
            i += 1
        else:
            if len != 0:
                len = lps[len-1]

            else:
                lps[i] = 0
                i += 1

def KMP(pat, txt):
    M = len(pat)
    N = len(txt)
 
    lps = [0]*M
    j = 0 

    computeLPSArray(pat, M, lps)
 
    i = 0
    while (N - i) >= (M - j):
        if pat[j] == txt[i]:
            i += 1
            j += 1
 
        if j == M:
            return True
            j = lps[j-1]

        elif i < N and pat[j] != txt[i]:
            if j != 0:
                j = lps[j-1]
            else:
                i += 1
    return False
 

stringMatching={
    'n':Naive,
    'rk':rabinKarp,
    'kmp':KMP
}

def parseResumes(path, match, algorithm='Naive'):
    global parseThread

    if os.path.exists(path)==False:
        socket_.emit('logging',{'data':'Invalid Path :('})
    else:
        flag=False
        for file in os.listdir(path):
            if event.is_set():
                break
            f=os.path.join(path, file)
            if os.path.isfile(f):
                if f[:5]=='.docx':
                    flag=True
                    doc=docx.document(f)
                    text=''
                    for para in doc.paragraphs:
                        text+=para.text
                elif f[:4]=='.pdf':
                    flag=True
                    with open(f, 'rb') as pdfFile:
                        pdfReader=PyPDF2.PdfFileReader(pdfFile)
                        pageObj=pdfReader.getPage(0)
                        text=pageObj.extractText()
                elif f[:4]=='.txt':
                    flag=True
                    with open(f, 'r') as txtFile:
                        text=txtFile.read()

                if stringMatching['algorithm'](text, match):
                        socket_.emit('logging', {'data':f'{file}'})

        if not flag:
            socket_.emit('logging', {'data':'No resumes found in the specified path'})
    parseThread=None

@app.route('/')
def index():
    return render_template('index.html', async_mode=socket_.async_mode)

@socket_.on('stop')
def stop(data):
    event.set()
    emit('logging', {'data':'Stopping the process'})

@socket_.on('parse')
def parse(data):
    message=data['data']
    global parseThread
    with parse_thread_lock:
        if parseThread is None:
            path=message['path']
            match=message['match']
            algo=message['algorithm']

            parseThread = socket_.start_background_task(parseResumes, match, path, algo)
            emit('logging', {'data': 'Started parsing'})
        else:
            emit('logging', {'data': 'Process already running'})

if __name__ == '__main__':
    socket_.run(app, debug=True)