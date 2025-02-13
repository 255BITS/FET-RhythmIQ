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
            return redirect(url_for('home'))
        else:
            error = result.get('error') if result else "Invalid credentials"
            return await render_template('login.html', error=error)
    return await render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
async def signup():
    if request.method == 'POST':
        data = await request.form
        email = data.get('email')
        password = data.get('password')
        try:
            result = await auth_module.signup(email, password)
            # send verification email
            verification_link = url_for('auth.verify_email', token=result['verification_token'], _external=True)
            subject = "Verify your email"
            message = f"Click this link to verify your email: {verification_link}"
            await send_mail(email, subject, message)
            flash("Signup successful! Please check your email to verify your account.")
            return redirect(url_for('auth.login'))
        except auth_module.UserExistsError as e:
            error = str(e)
            return await render_template('signup.html', error=error)
    return await render_template('signup.html')

@auth_bp.route('/verify/<token>')
async def verify_email(token):
    verified = await auth_module.verify(token)
    if verified:
        flash("Email verified successfully!")
        return redirect(url_for('auth.login'))
    else:
        flash("Invalid or expired verification token.")
        return redirect(url_for('auth.signup'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
async def forgot_password():
    if request.method == 'POST':
        data = await request.form
        email = data.get('email')
        token = await auth_module.forgot_password(email)
        if token:
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            subject = "Reset your password"
            message = f"Click this link to reset your password: {reset_link}"
            await send_mail(email, subject, message)
            flash("Password reset email sent. Please check your email.")
            return redirect(url_for('auth.login'))
        else:
            flash("Email not found.")
            return await render_template('forgot_password.html')
    return await render_template('forgot_password.html')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
async def reset_password(token):
    if request.method == 'POST':
        data = await request.form
        new_password = data.get('password')
        try:
            success = await auth_module.reset_password(token, new_password)
            if success:
                flash("Password reset successfully!")
                return redirect(url_for('auth.login'))
            else:
                flash("Invalid or expired reset token.")
        except Exception as e:
            flash(str(e))
    return await render_template('reset_password.html', token=token)
