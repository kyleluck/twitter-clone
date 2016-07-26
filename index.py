from flask import Flask, redirect, session, render_template, request
from werkzeug.security import generate_password_hash, check_password_hash
import pg

db = pg.DB(dbname='twitter')

app = Flask('twitter-app')

@app.route('/')
def show_public():
    if 'user' in session:
        tweets = db.query('''
            select
                tweet.content,
                tweet.image,
                tweet.category,
                tweet.created_at,
                user_table.username,
                user_table.userfull,
                user_table.avatar,
                (case when (now() - tweet.created_at > '59 minutes'::interval)
                	then to_char(tweet.created_at, 'Month DD')
                	else concat(to_char(age(now(), tweet.created_at), 'MI'), ' mins ago')
                	end) as time_display
            from
                tweet
            inner join
                user_table on tweet.user_id = user_table.id
            order by
                tweet.created_at desc''').namedresult()
        return render_template('public.html',
           tweets = tweets)
    else:
        return redirect('/login')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/processlogin', methods=['POST'])
def process_login():
    username = request.form['username']
    password = request.form['password']

    # find user by username
    user = db.query("select username, password from user_table where username = $1", username)
    if len(user.namedresult()) >= 1:
        # check that password matches. if so, redirect to home page otherwise redirect to login
        check_password = check_password_hash(user.namedresult()[0].password, password)
        if check_password:
            session['user'] = username
            return redirect('/')

    return render_template('login.html',
        errormessage = True)

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/processsignup', methods=['POST'])
def process_signup():
    username = request.form['username']
    password = request.form['password']
    userfull = request.form['userfull']
    bio = request.form['bio']
    website = request.form['website']
    hashed_password = generate_password_hash(password)

    # insert user into the database
    db.insert('user_table', username=username, password=hashed_password, userfull=userfull, bio=bio, website=website)

    return redirect('/login')

@app.route('/timeline')
def timeline():
    return 'timeline page'

# Secret key for session
app.secret_key = 'CSF686CCF85C6FRTCHQDBJDXHBHC1G478C86GCFTDCR'

if __name__ == '__main__':
    # debugging
    app.debug = True
    app.run(debug=True)
