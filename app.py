import this
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

def Naive(text, match, file):
    # pattern must be shorter than text
    count = 0
    if len(match) > len(text):
        return -1
 
    for i in range(len(text) - len(match) + 1):
        for j in range(len(match)):
            if text[i+j] != match[j] and text[i+j].lower() != match[j].lower():
                break
 
        if j == len(match)-1:
            if match.lower()==text[i:i+len(match)].lower():
                socket_.emit('logging', {'data':f'{file}: {text[i:i+len(match)]}'})
                count +=1

    socket_.emit('logging', {'data':f'"{file}"' ' Completed - No More Matches 🚫'})
    socket_.emit('logging', {'data':'Total Occcurence of 'f'"{match}" ➡️ {count}'})
    return False


def rabinKarp(text, match, file, q=101, d=256):
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
                socket_.emit('logging', {'data':f'{file}: {text[i:i+len(match)]}'})
                #return True

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

def KMP(pat, txt, file):
    pat, txt=txt, pat
    org_pat = pat
    org_txt = txt
    M = len(pat)
    N = len(txt)
    lps = [0]*M
    j = 0 
    k = 0
    computeLPSArray(org_pat.lower(), M, lps)
    count = 0
    i = 0
    while i < N:
        if org_pat[j].lower() == org_txt[i].lower():
            i += 1
            j += 1
 
        if j == M:
            print ("pat:",org_pat[0],"text:",org_txt[i-len(org_pat)])
            if(ord(org_pat[0]) >= 65 and ord(org_pat[0])< 91 and ord(org_pat[0]) +32 == ord(org_txt[i-len(org_pat)])):
                socket_.emit('logging', {'data':f'{file}: {org_txt[(i-len(org_pat)):((i-len(org_pat)) + len(org_pat))]}'})
                count+=1
                k+=1
                j= lps[j-1]
            elif(ord(org_pat[0]) >= 97 and ord(org_pat[0]) < 123 and ord(org_pat[0]) == ord(org_txt[i-len(org_pat) + 32])):
                socket_.emit('logging', {'data':f'{file}: {org_txt[(i-len(org_pat)):((i-len(org_pat)) + len(org_pat))]}'})
                count+=1
                j= lps[j-1]
            else:
                count +=1
                socket_.emit('logging', {'data':f'{file}: {org_txt[(i-len(org_pat)):((i-len(org_pat)) + len(org_pat))]}'})
                j= lps[j-1]
            
        elif i < N and org_pat[j].lower() != org_txt[i].lower():
            if j != 0:
                j = lps[j-1]
            else:
                i += 1
    socket_.emit('logging', {'data':f'"{file}"' ' Completed - No More Matches 🚫'})
    socket_.emit('logging', {'data':'Total Occcurence of 'f'"{pat}" ➡️ {count}'})
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
                socket_.emit('logging', {'data':f'Scanning {file}'})
                if f[-5:]=='.docx':
                    flag=True
                    doc=docx.document(f)
                    text=''
                    for para in doc.paragraphs:
                        text+=para.text
                elif f[-4:]=='.pdf':
                    flag=True
                    with open(f, 'rb') as pdfFile:
                        pdfReader=PyPDF2.PdfFileReader(pdfFile)
                        pageObj=pdfReader.getPage(0)
                        text=pageObj.extractText()
                elif f[-4:]=='.txt':
                    flag=True
                    with open(f, 'r', encoding='utf8') as txtFile:
                        text=txtFile.read()

                if flag:
                    stringMatching[algorithm](text, match, file)

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
            print(algo)

            parseThread = socket_.start_background_task(parseResumes, path, match, algo)
            emit('logging', {'data': 'Started parsing'})
        else:
            emit('logging', {'data': 'Process already running'})

if __name__ == '__main__':
    socket_.run(app, debug=True)