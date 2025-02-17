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
            verification_link = url_for('auth.verify_email', token=result['verification_token'], _external=True)
            subject = "Verify your email"
            message = f"Click this link to verify your email: {verification_link}"
            await send_mail(email, subject, message)
            await flash("Signup successful! Please check your email to verify your account.")
            if request.headers.get("HX-Request"):
                # After successful signup via HTMX, load the login form in the modal
                return await render_template('login.html', modal=True)
            return redirect(url_for('auth.login'))
        except auth_module.UserExistsError as e:
            error = str(e)
            if request.headers.get("HX-Request"):
                return await render_template('signup.html', error=error, modal=True)
            return await render_template('signup.html', error=error)
    if request.headers.get("HX-Request"):
        return await render_template('signup.html', modal=True)
    return await render_template('signup.html')

@auth_bp.route('/verify/<token>')
async def verify_email(token):
    verified = await auth_module.verify(token)
    if verified:
        await flash("Email verified successfully!")
        return redirect(url_for('auth.login'))
    else:
        await flash("Invalid or expired verification token.")
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
            await flash("Password reset email sent. Please check your email.")
            if request.headers.get("HX-Request"):
                # Close the modal on successful password reset request
                return "<script>document.getElementById('loginModal').style.display='none';</script>"
            return redirect(url_for('auth.login'))
        else:
            await flash("Email not found.")
            if request.headers.get("HX-Request"):
                return await render_template('forgot_password.html', modal=True)
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
                await flash("Password reset successfully!")
                return redirect(url_for('auth.login'))
            else:
                await flash("Invalid or expired reset token.")
        except Exception as e:
            await flash(str(e))
    return await render_template('reset_password.html', token=token)

@auth_bp.route('/logout')
async def logout():
    session.pop('token', None)
    return redirect(url_for('home'))
