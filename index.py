from flask import Flask, redirect, session, render_template, request
from werkzeug.security import generate_password_hash, check_password_hash
import pg

db = pg.DB(dbname='twitter')

app = Flask('twitter-app')

@app.route('/')
def show_public():
    #print "generated password is %r" % generate_password_hash('test3456')
    print "id is: %r" % session['id']
    if 'user' in session:
        tweets = db.query('''
            select
                tweet.id,
                tweet.content,
                tweet.image,
                tweet.user_id,
                tweet.created_at,
                (case when (now() - tweet.created_at > '59 minutes'::interval)
                	then to_char(tweet.created_at, 'Month DD')
                	else concat(to_char(age(now(), tweet.created_at), 'MI'), ' mins ago')
                	end) as time_display,
                (case when exists
                    (select * from likes where tweet_id = tweet.id and user_id = $1)
                    then true else false end) as liked,
                user_table.username,
                user_table.userfull,
                user_table.avatar,
                False as retweet,
                'None' as retweet_username
            from
                tweet
            inner join
                user_table on tweet.user_id = user_table.id
            union all
            select
                tweet.id,
                tweet.content,
                tweet.image,
                tweet.user_id,
                rt.created_at,
                (case when (now() - tweet.created_at > '59 minutes'::interval)
                    then to_char(tweet.created_at, 'Month DD')
                    else concat(to_char(age(now(), tweet.created_at), 'MI'), ' mins ago')
                    end) as time_display,
                (case when exists (select * from likes where tweet_id = tweet.id and user_id = $1) then true else false end) as liked,
                user_table.username,
                user_table.userfull,
                user_table.avatar,
                True as retweet,
                (select username from user_table where id = rt.user_id) as retweet_username
            from
                tweet
            left outer join retweet AS rt ON rt.tweet_id = tweet.id
            left outer join
                user_table on tweet.user_id = user_table.id
            where
                tweet.id = tweet_id
            order by created_at desc
            ''', session['id']).namedresult()
        return render_template('public.html',
            title = "What's Happening",
            tweets = tweets)
    else:
        return redirect('/login')

@app.route('/profile/<username>')
def profile(username):
    if username:

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
                username ilike $1
            ''', username).namedresult()

        if len(user_info) > 0:
            user_id = user_info[0].id
        else:
            return redirect('/404')

        # get followers and following stats
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
        		  user_id = $1
        		group by
        		  follower.user_id) as followers_query on user_id = followed_by;
                ''', user_id).namedresult()

        # get current tweets for this profile user
        user_tweets = db.query('''
            select
                tweet.id,
                tweet.content,
                tweet.image,
                tweet.user_id,
                tweet.created_at,
                (case when (now() - tweet.created_at > '59 minutes'::interval)
                    then to_char(tweet.created_at, 'Month DD')
                    else concat(to_char(age(now(), tweet.created_at), 'MI'), ' mins ago')
                    end) as time_display,
                (case when exists
                    (select * from likes where tweet_id = tweet.id and user_id = $1)
                    then true else false end) as liked,
                user_table.username,
                user_table.userfull,
                user_table.avatar,
                False as retweet,
                'None' as retweet_username
            from
                tweet
            left outer join
                user_table on tweet.user_id = user_table.id
            where
                user_id = $1
            union all
            select
                tweet.id,
                tweet.content,
                tweet.image,
                tweet.user_id,
                rt.created_at,
                (case when (now() - tweet.created_at > '59 minutes'::interval)
                    then to_char(tweet.created_at, 'Month DD')
                    else concat(to_char(age(now(), tweet.created_at), 'MI'), ' mins ago')
                    end) as time_display,
                (case when exists (select * from likes where tweet_id = tweet.id and user_id = $1) then true else false end) as tweet_liked,
                user_table.username,
                user_table.userfull,
                user_table.avatar,
                True as retweet,
                (select username from user_table where id = rt.user_id) as retweet_username
            from
                tweet
            left outer join retweet AS rt ON rt.tweet_id = tweet.id
            left outer join
                user_table on tweet.user_id = user_table.id
            where
                tweet.id = tweet_id and rt.user_id = $1
            order by created_at desc
            ''', user_id).namedresult()

        # get number of tweets for this profile user
        num_tweets = db.query('select count(id) as num from tweet where user_id = $1', user_id).namedresult()

        if len(user_following) >= 1:
            following = user_following[0]
        else:
            following = None

        # does the logged in user currently follow this profile user?
        currently_following = db.query("select count(id) from follower where user_id = %d and followed_by = %d" % (user_id, session['id'])).namedresult()

        if currently_following[0].count > 0:
            user_is_following = True
        else:
            user_is_following = False

        return render_template('profile.html',
            title = "@%s" % username,
            user_info = user_info[0],
            user_following = following,
            user_tweets = user_tweets,
            num_tweets = num_tweets[0],
            user_is_following = user_is_following)
    else:
        return redirect('/404')

@app.route('/timeline')
def timeline():
    user_id = session['id']
    print "session id is: %r" % user_id
    tweets_retweets = db.query('''
        select
            tweet.id,
            tweet.content,
            tweet.image,
            tweet.category,
            tweet.created_at,
            (case when (now() - tweet.created_at > '59 minutes'::interval)
                then to_char(tweet.created_at, 'Month DD')
                else concat(to_char(age(now(), tweet.created_at), 'MI'), ' mins ago')
                end) as time_display,
            (case when exists (select * from likes where tweet_id = tweet.id and user_id = $1) then true else false end) as liked,
            user_table.username,
            user_table.userfull,
            user_table.avatar,
            False as retweet,
            'None' as retweet_username
        from
            tweet
        left outer join
        	retweet on tweet.id = retweet.tweet_id
        left outer join
            user_table on tweet.user_id = user_table.id
        where
            tweet.user_id = $1 or
            tweet.user_id in (
                select user_id from follower where followed_by = $1
            )
        union all
        select
            tweet.id,
            tweet.content,
            tweet.image,
            tweet.category,
            rt.created_at,
            (case when (now() - tweet.created_at > '59 minutes'::interval)
                then to_char(tweet.created_at, 'Month DD')
                else concat(to_char(age(now(), tweet.created_at), 'MI'), ' mins ago')
                end) as time_display,
            (case when exists (select * from likes where tweet_id = tweet.id and user_id = $1) then true else false end) as liked,
            user_table.username,
            user_table.userfull,
            user_table.avatar,
            True as retweet,
            (select username from user_table where id = rt.user_id) as retweet_username
        from
            tweet
        left outer join retweet AS rt ON rt.tweet_id = tweet.id
        left outer join
            user_table on tweet.user_id = user_table.id
        where
            tweet.id = tweet_id and (tweet.user_id = $1 or
            tweet.user_id in (
                select user_id from follower where followed_by = $1
            ))
        order by created_at desc
    ''', user_id).namedresult()

    return render_template('timeline.html',
        title = "Your Timeline",
        tweets = tweets_retweets)

@app.route('/follow', methods=['GET'])
def follow():
    user_to_follow = request.args.get('userid')
    current_profile = request.args.get('current_profile')
    current_user_id = session['id']

    # insert into follower table
    db.insert('follower', user_id=user_to_follow, followed_by=current_user_id)

    return redirect('/profile/%s' % current_profile)

@app.route('/tweet', methods=['POST'])
def tweet():
    tweet = request.form['tweet']
    user_id = session['id']

    #insert tweet
    db.insert('tweet', content=tweet, user_id=user_id)

    return redirect('/timeline')

@app.route('/like/<tweet_id>')
def like(tweet_id):
    user_id = session['id']

    db.insert('likes', user_id=user_id, tweet_id=tweet_id)

    # redirect to the referrer
    return redirect(request.referrer);


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', title = "Login")
    else:
        username = request.form['username']
        password = request.form['password']

        # find user by username
        user = db.query("select id, username, password from user_table where username ilike $1", username)
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


@app.route('/retweet', methods=["POST"])
def retweet():
    user_id = session['id']
    tweet_id = request.form['tweet_id']

    db.insert('retweet', user_id=user_id, tweet_id=tweet_id)

    # redirect to the referrer
    return redirect(request.referrer);



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html', title = "Register")
    else:
        username = request.form['username']
        password = request.form['password']
        userfull = request.form['userfull']
        bio = request.form['bio']
        website = request.form['website']
        hashed_password = generate_password_hash(password)
        avatar = request.form['avatar']

        # insert user into the database
        db.insert('user_table', username=username, password=hashed_password, userfull=userfull, bio=bio, website=website, avatar=avatar)

        return redirect('/login')

@app.route('/logout')
def logout():
    if session['user']:
        del session['user']
        del session['id']
    return redirect('/login')

# simple error page
@app.route('/404')
def not_found():
    return render_template('404.html', title="404")


# Secret key for session
app.secret_key = 'CSF686CCF85C6FRTCHQDBJDXHBHC1G478C86GCFTDCR'

if __name__ == '__main__':
    # debugging
    app.debug = True
    app.run(debug=True)
