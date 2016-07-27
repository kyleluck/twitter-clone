from flask import Flask, redirect, session, render_template, request
from werkzeug.security import generate_password_hash, check_password_hash
import pg

db = pg.DB(dbname='twitter')

app = Flask('twitter-app')

@app.route('/')
def show_public():
    #print "generated password is %r" % generate_password_hash('test3456')
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
        return render_template('timeline.html',
            title = "What's Happening",
            tweets = tweets)
    else:
        return redirect('/login')

@app.route('/profile', methods=['GET'])
def profile():
    if request.args.get('username'):
        username = request.args.get('username')
        # get user information from db
        user_info = db.query('''
            select
                user_table.id,
                user_table.bio,
                user_table.username,
                user_table.userfull,
                user_table.website,
                user_table.avatar,
                user_table.joined,
                to_char(joined, 'Month YYYY') as joined_display
            from
                user_table
            where
                username = $1
            ''', username).namedresult()

        user_id = user_info[0].id

        user_following = db.query('''
            select
        	  follows, followers
        	from (
        		select
        			count(followed_by) as followers,
        			followed_by
        		from
        		  follower
        		where
        		  followed_by = $1
        		group by
        		  followed_by) as follows_query
        		full outer join
        		  (select
        			count(user_id) as follows,
        			user_id
        		from
        		  follower
        		where
        		  user_id = $2
        		group by
        		  follower.user_id) as followers_query on user_id = followed_by;
                ''', user_id, user_id).namedresult()

        user_tweets = db.query('''
            select
                *,
                (case when (now() - tweet.created_at > '59 minutes'::interval)
                    then to_char(tweet.created_at, 'Month DD')
                    else concat(to_char(age(now(), tweet.created_at), 'MI'), ' mins ago')
                    end) as time_display
            from
                tweet
            where
                user_id = $1''', user_id).namedresult()

        num_tweets = db.query('select count(id) as num from tweet where user_id = $1', user_id).namedresult()

        if len(user_following) >= 1:
            following = user_following[0]
        else:
            following = None

        return render_template('profile.html',
            title = "@%s" % user_info[0].username,
            user_info = user_info[0],
            user_following = following,
            user_tweets = user_tweets,
            num_tweets = num_tweets[0])
    else:
        return redirect('/404')

@app.route('/timeline')
def timeline():
    user_id = session['id']
    timeline_query = db.query('''
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
        full outer join
            user_table on tweet.user_id = user_table.id
        where
            tweet.user_id = $1 or
            tweet.user_id in (
                select user_id from follower where followed_by = $1
            )
        order by
            time_display asc
        ''', user_id).namedresult()
    return render_template('timeline.html',
        title = "@%s's Timeline" % timeline_query[0].username,
        tweets = timeline_query)


@app.route('/login')
def login():
    return render_template('login.html', title = "Login")


@app.route('/processlogin', methods=['POST'])
def process_login():
    username = request.form['username']
    password = request.form['password']

    # find user by username
    user = db.query("select id, username, password from user_table where username = $1", username)
    if len(user.namedresult()) >= 1:
        # check that password matches. if so, redirect to home page otherwise redirect to login
        check_password = check_password_hash(user.namedresult()[0].password, password)
        if check_password:
            session['user'] = username
            session['id'] = user.namedresult()[0].id
            return redirect('/')

    return render_template('login.html',
        errormessage = True,
        title = "Login")

@app.route('/signup')
def signup():
    return render_template('signup.html', title = "Register")

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

@app.route('/logout')
def logout():
    if session['user']:
        del session['user']
        del session['id']
    return redirect('/login')

# Secret key for session
app.secret_key = 'CSF686CCF85C6FRTCHQDBJDXHBHC1G478C86GCFTDCR'

if __name__ == '__main__':
    # debugging
    app.debug = True
    app.run(debug=True)
