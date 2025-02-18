from quart import Blueprint, render_template, request, redirect, url_for, session, flash
import pg_simple_auth.auth as auth_module
from mail import send_mail

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'POST':
        data = await request.form
        email = data.get('email')
        password = data.get('password')
        result = await auth_module.login(email, password)
        if result and 'token' in result:
            session['token'] = result['token']
            if request.headers.get("HX-Request"):
                return await render_template('_auth.html')
            return redirect(url_for('home'))
        else:
            error = result.get('error') if result else "Invalid credentials"
            if request.headers.get("HX-Request"):
                return await render_template('_auth.html', error=error)
            return await render_template('login.html', error=error)
    if request.headers.get("HX-Request"):
        return await render_template('login.html', modal=True)
    return await render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
async def signup():
    if request.method == 'POST':
        data = await request.form
        email = data.get('email')
        password = data.get('password')
        try:
            result = await auth_module.signup(email, password)
            await auth_module.verify(result['verification_token'])

            # send verification email
            result = await auth_module.login(email, password)
            if result and 'token' in result:
                session['token'] = result['token']
            if request.headers.get("HX-Request"):
                return await render_template('_auth.html')
            return redirect(url_for('auth.login'))
        except auth_module.UserExistsError as e:
            error = str(e)
            if request.headers.get("HX-Request"):
                return await render_template('_auth.html', error=error)
            return await render_template('signup.html', error=error)
    if request.headers.get("HX-Request"):
        return await render_template('signup.html', modal=True)
    return await render_template('signup.html')

@auth_bp.route('/logout')
async def logout():
    session.pop('token', None)
    return redirect(url_for('home'))
