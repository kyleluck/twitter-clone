from flask import Flask, redirect, session, render_template, request
import pg

db = pg.DB(dbname='twitter')

app = Flask('twitter-app')

@app.route('/')
def show_public():
    tweets = db.query("select * from tweet").namedresult()
    return render_template('public.html',
       tweets = tweets)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/processlogin')
def process_login():
    return 'process_login'

@app.route('/signup')
def signup():
    return 'signup page'

@app.route('/timeline')
def timeline():
    return 'timeline page'

if __name__ == '__main__':
    app.run(debug=True)
