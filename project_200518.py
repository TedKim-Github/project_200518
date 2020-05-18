from flask import Flask, render_template, request, session, redirect
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import re
import os
import base64
from konlpy.tag import Kkma
kkma = Kkma()
import pymysql

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

app = Flask(__name__, template_folder='project', static_folder="project_css")
app.env = "development"
app.debug = True
app.secret_key = "session"

# db 접속
db = pymysql.connect(
    user = 'root',
    passwd = 'root',
    host = 'localhost',
    db = 'project',
    charset = 'utf8',
    cursorclass = pymysql.cursors.DictCursor)

# 로그인 아웃/ 회원가입/ 탈퇴
@app.route('/')
def index():
    cursor = db.cursor()
    cursor.execute("select id from user")
    
    return render_template('index.html', user=session.get('user'))  
    
## 로그인
@app.route('/login', methods = ['get', 'post'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    cursor= db.cursor()
    cursor.execute(f"""
        select id, name from user
        where id ='{ request.form['userid'] }' and
            password= SHA2('{ request.form['password'] }', 256) 
        """)
    user = cursor.fetchone()

    if user:
        session['user'] = user
        return redirect('/')
    else:
        return render_template('login.html', msg="로그인 정보를 확인하세요")

## 로그아웃
@app.route('/logout')
def logout():
    
    session.pop('user') 
    
    return redirect('/') 

## 회원가입
@app.route('/join', methods = ['get', 'post'])
def join():
    if request.method == 'GET':
        return render_template('join.html')
    
    cursor= db.cursor()
    cursor.execute(f"""
        INSERT INTO user VALUES ('{request.form['userid']}','{request.form['username']}',
            SHA2('{ request.form['password'] }', 256))
        
        """)
    db.commit()
    user = cursor.fetchone()
    
   
    return render_template('login.html', user=session.get('user'))  

## 회원탈퇴
@app.route('/withdrawal')
def withdrawal():
   
    cursor= db.cursor()
    cursor.execute(f"""
        delete from user where id='{session.pop('user')['id']}'
        
        """)
    db.commit()
    
    return redirect('/') 


# 뉴스

@app.route('/news/ranking', methods=['get', 'post'])
def news():

    if request.method == 'GET':
        return render_template('news.html')

    url = 'https://media.daum.net/ranking'
    # query = {'regDate': request.form.get('int_date')}
    query = request.form.get('int_date')
    # res = requests.get(url, param=query)
    url = url + '?regDate=' + query
    res = requests.get(url)
    soup = BeautifulSoup(res.content, 'html.parser')

    soup = soup.select('#kakaoContent')[0]


    extracts = [dict(
        title= re.sub('\s+', '', a.get_text().replace('\n', '')),
        url= a['href']
    ) for a in soup.select('a.link_txt')]
 
    return render_template('news.html', news= extracts)



@app.route('/news/<words>')
def news_words(words):

    url1= request.args.get('url')

    res = requests.get(url1)
    soup = BeautifulSoup(res.content, 'html.parser')

    str = ''

    for x in range(0, 50):
        if soup.select("#harmonyContainer")[x].get_text() is not None:
            str = str + soup.select("#harmonyContainer")[x].get_text()
            break

    # soup = BeautifulSoup(res.content, 'html.parser')
    # words = request.form.get('res').strip()
    words = kkma.pos(str)
    words = [w for w in words if w[1]] # in ['NNG', 'NNP']]

    words = [(w, words.count(w)) for w in set(words)]
    words = sorted(words, key=lambda x: x[1], reverse=True)


    return render_template('news_words.html', words=words)


  


# 이미지 다운로드

@app.route('/download/<keyword>', methods=['get', 'post'])
def download(keyword):
    if request.method == 'GET':
        return render_template('download.html', keyword=keyword)
    
    driver= webdriver.Chrome('chromedriver',options=options)
    driver.implicitly_wait(3)
    
    url= f"https://www.google.com/search?q={keyword}&tbm=isch"
    driver.get(url)

    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    images = soup.select('img.rg_i')
    
    # 디렉토리 생성
    os.makedirs(f'project/download/{keyword}', exist_ok=True)

    # 링크저장
    img_dumps = []
    img_links = []
    for tag in soup.select('img.rg_i'):
        if tag.get('src') is None:
            img_links.append(tag.get('data-src'))

        else: img_dumps.append(tag.get('src'))

    # 다운로드
    for i, link in enumerate(img_links):
        driver = requests.get(link)
        with open(f'project/download/{keyword}/{i}.jpg', 'wb') as f:
            f.write(driver.content)

    for i, dump in enumerate(img_dumps):    
        img_data = base64.b64decode(dump.split(',')[1])
        with open(f'project/download/{keyword}/{i}_.jpg', 'wb') as f:
            f.write(img_data) 

    return render_template('download.html', keyword=keyword, img_links=img_links, img_dumps=img_dumps)



app.run()