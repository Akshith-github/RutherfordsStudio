from flask import render_template ,redirect ,request, url_for, abort ,flash ,request, current_app, make_response #, session
from flask_login import  login_required ,current_user # logout_user,
from flask_sqlalchemy import get_debug_queries
from .. import db
from ..models import User#,Permission
# from ..email import send_email
from . import main
from .forms import EditProfileForm, EditProfileAdminForm , PostForm , CommentForm#,NameForm
from ..models import User , Role , Permission , Post , Comment
from ..decorators import admin_required, permission_required
import os,requests
import textwrap

@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration, query.context))
    return response

@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'

@main.route('/', methods=['GET', 'POST'])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,show_followed=show_followed,  pagination=pagination,type=type,enumerate=enumerate,pagination_endpoint=".index")
    # posts = Post.query.order_by(Post.timestamp.desc()).all()
    # return render_template('index.html', form=form, posts=posts,type=type,enumerate=enumerate)
    # form = NameForm()
    # if form.validate_on_submit():
    #     user = User.query.filter_by(username=form.name.data).first()
    #     if user is None:
    #         user = User(username=form.name.data)
    #         db.session.add(user)
    #         session['known'] = False
    #         if current_app.config['FLASKY_ADMIN']:
    #             send_email(current_app.config['FLASKY_ADMIN'], 'New User',
    #                        'mail/new_user', user=user)
    #     else:
    #         session['known'] = True
    #     session['name'] = form.name.data
    #     return redirect(url_for('.index'))
    # return render_template('index.html',
    #                        form=form, name=session.get('name'),
    #                        known=session.get('known', False))


@main.route("/home")
@login_required
def home():
    from .api_fxns import def_extract,fl_extract,meta_extract,shortdef_extract
    url=os.environ.get('RECOMMEND_API')
    data= requests.api.get(url,params={'n':5})
    url_2=os.environ.get('RANDOM_WORD_API')
    word=requests.api.get(url_2,params={'number':1})
    url_3=os.environ.get('WORD_MEANING_API')
    key=os.environ.get('WORD_MEANING_API_KEY')
    req=requests.api.get(url_3+word.text[2:-2],params={'key':key})
    meanings_json = req.json()
    # print("||"+word.text[2:-2]+"||",meanings_json)
    if(type(meanings_json[0])==dict):
        defs,vd,examples=def_extract(meanings_json)
        poss=fl_extract(meanings_json)
        stems,offensive = meta_extract(meanings_json)
        meanings=shortdef_extract(meanings_json)
        # print("defs",defs,"vd",vd,"examples",examples,"poss",poss,"stems",stems,"offensive",offensive,"meanings",meanings,sep="\n"*3)
        return render_template('home.html',
        data1=data.json(),keys=list(data.json().keys())[1:],textwrap=textwrap,word=word.text[2:-2],offensive=offensive,
        defs=meanings,poss=poss,
        stems=stems,examples=examples,txt="",enumerate=enumerate,len=len,str=str)
    else:
        shortdefs=[]
        request_text = req.text
    # shortdefs=[]
    # print("||"+word+"||",meanings_json)
    return render_template('home.html',
        data1=data.json(),keys=list(data.json().keys())[1:],textwrap=textwrap,word=word.text[2:-2],offensive=[],
        defs=[],poss=[],examples=[], stems=[],txt=request_text,enumerate=enumerate,len=len)

@main.route("/home/<string:word>")
@login_required
def home_word(word):
    from .api_fxns import  shortdef_extract,fl_extract,meta_extract,uros_extract,def_extract
    url=os.environ.get('RECOMMEND_API')
    data= requests.api.get(url,params={'n':5})
    # url_2=os.environ.get('RANDOM_WORD_API')
    # word=requests.api.get(url_2,params={'number':1})
    url_3=os.environ.get('WORD_MEANING_API')
    key=os.environ.get('WORD_MEANING_API_KEY')
    req=requests.api.get(url_3+word,params={'key':key})
    meanings_json = req.json()
    # print("||"+word+"||",meanings_json)
    if(type(meanings_json[0])==dict):
        defs,vd,examples=def_extract(meanings_json)
        poss=fl_extract(meanings_json)
        stems,offensive = meta_extract(meanings_json)
        meanings=shortdef_extract(meanings_json)
        # print("defs",defs,"vd",vd,"examples",examples,"poss",poss,"stems",stems,"offensive",offensive,"meanings",meanings,sep="\n"*3)
        return render_template('home.html',
        data1=data.json(),keys=list(data.json().keys())[1:],textwrap=textwrap,word=word,offensive=offensive,
        defs=meanings,poss=poss,
        stems=stems,examples=examples,txt="",enumerate=enumerate,len=len,str=str)
    else:
        shortdefs=[]
        request_text = req.text
    # shortdefs=[]
    # print("||"+word+"||",meanings_json)
    return render_template('home.html',
        data1=data.json(),keys=list(data.json().keys())[1:],textwrap=textwrap,word=word,offensive=[],
        defs=[],poss=[],examples=[], stems=[],txt=request_text,enumerate=enumerate,len=len)


@main.route("/page/<string:name>")
@login_required
def page(name):
    return render_template(name)

@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    # print(url_for(request.endpoint,username=username),"\n"*8)
    # return render_template('user.html',context={'username':username,'user':'user', 'posts':posts, 'pagination':pagination,'type':type,'enumerate':enumerate,'pagination_endpoint':request.endpoint})
    return render_template('user.html',user=user, posts=posts, pagination=pagination,type=type,enumerate=enumerate,pagination_endpoint=".user",username=username)
    # posts = user.posts.order_by(Post.timestamp.desc()).all()
    # return render_template('user.html', user=user, posts=posts  ,enumerate=enumerate)

def redirectfonts():
    return redirect("https://fonts.googleapis.com/css?family=Jost:100,200,300,400,500,600,700,800,900,100i,200i,300i,400i,500i,600i,700i,800i,900i&display=swap")

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    # print(form.data,request.endpoint)
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    # print(form.data,request.endpoint) 
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

@main.route("/message",methods=['GET', 'POST'])
def message_(message_name,message_desc,extra,link,link_txt):
    return render_template('error_msg.html',error_name=message_name,error_desc=message_desc,extra=extra, link=link , link_txt = link_txt
    ),200

@main.route("/codearena")
@login_required
def redirect_to_codearena():
    return message_(message_name='Access only to klu mail domain users',message_desc='Code arena will be accessible to all users on the next version launch', extra= 'click on link to check code arena',
    link='https://sites.google.com/klu.ac.in/frustratedtycoons/home',link_txt='Mini code arena')
    """redirect(url_for('main.message_',message_name='Access only to klu mail domain users',message_desc='Code arena will be accessible to all users on the next version launch', extra= 'click on link to check code arena',
    link='https://sites.google.com/klu.ac.in/frustratedtycoons/home',link_txt='Mini code arena'))"""

@main.route('/explorer')
def open_explorer():
    return render_template('explorer.html')

@main.route('/library2')
def open_library2():
    return render_template('library2.html')


@main.route('/contactus')
def open_contactus():
    return render_template('contact_us.html')

@main.route('/library')
def open_library():
    import pandas as pd
    booksDf=pd.read_csv("65_books.csv").sample(n=12).values
    return render_template('library.html',booksDf=booksDf,type=type,eval=eval,len=len,str=str,enumerate=enumerate)

@main.route('/blogs')
def open_blogs():
    return render_template('blog_gym.html')

@main.route('/Resources')
def open_resources():
    return render_template('resources.html')

@main.route('/book/<isbn>')
def open_book(isbn):
    import pandas as pd
    booksDF=pd.read_csv("65_books.csv")
    if not(isbn in booksDF.ISBN.values):
        flash(f'Requested Book with {isbn} is not still available in library or the isbn is wrong..')
        return redirect(url_for('main.open_library'))
    book=booksDF[booksDF.ISBN==isbn].values
    bookDict=booksDF[booksDF.ISBN==isbn].to_dict()
    # print(book[0],len(book))
    # from .api_fxns import def_extract,fl_extract,meta_extract,shortdef_extract
    url=os.environ.get('RECOMMEND_API')
    # print(book[0][2],type(book[0][2]))
    # print(len(book))
    # print(book)
    try:
        data= requests.api.get(url,params={'n':5,'isbn':isbn})
        keys=list(data.json().keys())[1:]
        data1=data.json()
    except:
        keys=[]
        data1=[]
    book=book[0]
    # input()
    print(data1)
    return render_template('bookPage.html',book=book,type=type,eval=eval,len=len,str=str,enumerate=enumerate,textwrap=textwrap,bookDict=bookDict,dict=dict,list=list,keys=keys,data1=data1,booksDF=booksDF)


@main.route('/codePlayground')
def open_code_ground():
    return render_template('Code Executer.html')

@main.route('/Courses')
def open_courses():
    return render_template('courses.html')


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
            current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post],enumerate=enumerate , form=form,
                            comments=comments, pagination=pagination)
    # return render_template('post.html', posts=[post],enumerate=enumerate)

@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash('The post has been updated.')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)

@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)

@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments, pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))