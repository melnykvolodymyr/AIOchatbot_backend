from flask import Blueprint, request, jsonify, session
from flask_session import Session
from flask_bcrypt import Bcrypt
from authlib.integrations.flask_client import OAuth
from sqlalchemy.exc import IntegrityError
import uuid
import datetime
import jwt
import string
import secrets
import requests

from auth_middleware import encode_auth_token, decode_auth_token, verify_token
from models import User, PassResetCode, db

bcrypt = Bcrypt()
oauth = OAuth()
server_session = Session()

auth_bp = Blueprint("auth_bp", __name__)

from config import ApplicationConfig

MAILGUN_DOMAIN = ApplicationConfig.MAILGUN_DOMAIN
MAILGUN_API_KEY = ApplicationConfig.MAILGUN_API_KEY
GOOGLE_CLIENT_ID = ApplicationConfig.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = ApplicationConfig.GOOGLE_CLIENT_SECRET
SECRET_KEY = ApplicationConfig.SECRET_KEY


@auth_bp.route("/signin", methods=["POST"])
def login():
    email = request.json["email"]
    password = request.json["password"]

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(message="The user doesn't exist"), 400

    password_hash = user.password_hash
    if not bcrypt.check_password_hash(password_hash, password):
        return jsonify({"error": "Unauthorized"}), 401

    # Generate the auth token
    auth_tokens = encode_auth_token(str(user.id))
    if auth_tokens:
        session["user_id"] = str(user.id)
        return (
            jsonify(
                message="Successfully logged in",
                access_token=auth_tokens["access_token"],
                refresh_token=auth_tokens["refresh_token"],
            ),
            200,
        )
    else:
        return (
            jsonify(message="Operation failed due to an unexpected error."),
            500,
        )


@auth_bp.route("/@me", methods=["GET"])
def get_current_user():

    user_id = session.get("user_id")
    # If no session, check request header token
    if not user_id:
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        # The token normally comes with the text 'Bearer ' prefix
        # Remove it to get the actual token
        if "Bearer " in token:
            token = token.replace("Bearer ", "")

        # Verify the token
        user_id = verify_token(token)
        if not user_id:
            return jsonify({"message": "Token is invalid!"}), 401
        session["user_id"] = user_id

    user = User.query.filter_by(id=user_id).first()
    if not user:
        session["user_id"] = None
        return jsonify(message="User not found"), 404

    return jsonify(id=user.id, email=user.email), 200


@auth_bp.route("/signup", methods=["POST"])
def register():
    email = request.json["email"]
    password = request.json["password"]

    if not email or not password:
        return jsonify(message="Invalid data request"), 404

    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify(message="User with the same email already exists"), 400

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
    unique_id = str(uuid.uuid4())
    new_user = User(
        id=unique_id,
        email=email,
        email_verified_at=None,
        username=None,
        password_hash=hashed_password,
        avatar_url="",
        bio="",
        location={},
        rating={},
        is_onboarded=False,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        gaming_platform_id=None,
        play_style_id=None,
        avatar_id=None,
        objective_id=None,
        source_id=None,
        source_type=1,
        stats_url="",
        social_url={},
        stats_id=None,
    )
    print("@@@@@@@@@")
    print(new_user)
    print("@@@@@@@@@")
    db.session.add(new_user)
    try:
        db.session.commit()
    except IntegrityError as e:
        print(e)
        db.session.rollback()
        return (
            jsonify(message="Operation failed due to an unexpected error."),
            500,
        )
    except Exception as e:
        print(e)
        # Log the error 'e' or print it to the console
        return jsonify(message="Operation failed due to an unexpected error."), 500
    return jsonify(message="User created successfully"), 200


@auth_bp.route("/signup/google_oauth", methods=["GET"])
def register_google_oauth():
    google = oauth.register(
        name="google",
        client_id=f"{GOOGLE_CLIENT_ID}",
        client_secret=f"{GOOGLE_CLIENT_SECRET}",
        access_token_url="https://accounts.google.com/o/oauth2/token",
        access_token_params=None,
        authorize_url="https://accounts.google.com/o/oauth2/auth",
        authorize_params=None,
        api_base_url="https://www.googleapis.com/oauth2/v1/",
        userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
        # This is only needed if using openId to fetch user info
        client_kwargs={"scope": "openid email profile"},
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    )

    token = google.authorize_access_token()
    user = token["userinfo"]
    return f"Welcome {user['email']}!"


# Revoke refresh token
@auth_bp.route("/refresh_token", methods=["POST"])
def get_refresh_token():
    old_refresh_token = request.json["refresh_token"]

    # Attempt to decode the token
    try:
        # Decode the token
        # Be sure to specify the correct algorithm used for the token
        decoded_token = jwt.decode(old_refresh_token, SECRET_KEY, algorithms=["HS256"])
        return jsonify(message="Token is valid", refresh_token=old_refresh_token), 200

    except jwt.ExpiredSignatureError:
        decoded_token = jwt.decode(
            old_refresh_token, options={"verify_signature": False}
        )
        user_id = decoded_token.get("sub")
        if user_id:
            refresh_token_payload = {
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1),
                "iat": datetime.datetime.utcnow(),
                "sub": user_id,
            }
            refresh_token = jwt.encode(
                refresh_token_payload, SECRET_KEY, algorithm="HS256"
            )
            return (
                jsonify(
                    message="New refresh token was created", refresh_token=refresh_token
                ),
                200,
            )
        else:
            return (
                jsonify(message="No user_id found in the token payload."),
                400,
            )

    except jwt.InvalidTokenError:
        return (
            jsonify(message="Token is invalid"),
            400,
        )
    except jwt.DecodeError:
        return (
            jsonify(message="Token is invalid"),
            400,
        )


@auth_bp.route("/token", methods=["POST"])
def get_auth_tokens():
    email = request.json["email"]
    password = request.json["password"]

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(message="The user doesn't exist"), 400

    password_hash = user.password_hash
    if not bcrypt.check_password_hash(password_hash, password):
        return jsonify({"error": "Unauthorized"}), 401

    # Generate the auth token
    auth_tokens = encode_auth_token(str(user.id))
    if auth_tokens:
        return (
            jsonify(
                access_token=auth_tokens["access_token"],
                refresh_token=auth_tokens["refresh_token"],
            ),
            200,
        )
    return jsonify({"message": "success"})


# Password_reset_request
@auth_bp.route("/password_reset_request", methods=["POST"])
def password_reset_request():
    email = request.json["email"]
    user = User.query.filter_by(email=email).first()
    if not user:
        return (
            jsonify(message="The user doesn't exist"),
            400,
        )
    pass_code_obj = PassResetCode.query.filter_by(email=email).first()

    # Generate password reset code
    pin_code = generate_password_reset_code()

    # Store infomation in table
    unique_id = str(uuid.uuid4())
    expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
    if pass_code_obj:
        pass_code_obj.pin_code = pin_code
        pass_code_obj.expires_at = expires_at
        db.session.commit()
    else:
        new_pass_code = PassResetCode(
            id=unique_id, email=email, pin_code=pin_code, expires_at=expires_at
        )
        db.session.add(new_pass_code)
        try:
            db.session.commit()
        except IntegrityError as e:
            print(e)
            db.session.rollback()
            return (
                jsonify(message="Operation failed due to an unexpected error."),
                500,
            )
        except Exception as e:
            print(e)
            # Log the error 'e' or print it to the console
            return jsonify(message="Operation failed due to an unexpected error."), 500

    # Send password reset email
    response = send_password_reset_email(email, pin_code)
    return jsonify({"message": "The verification code is sent to your email"}), 200


def generate_password_reset_code(length=8):
    # Generate a secure random string for password reset
    characters = string.ascii_letters + string.digits
    reset_code = "".join(secrets.choice(characters) for i in range(length))
    return reset_code


def send_password_reset_email(email, pin_code):
    return requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": f"Dood Team <mail@{MAILGUN_DOMAIN}>",
            "to": [email],
            "subject": f"Password verification code: {pin_code}",
            "html": password_reset_email_template(pin_code),
        },
    )


def password_reset_email_template(verify_code):
    return f"""
    <html>
        <body style='text-align: center'>
            <h1>Account verification</h1>
            <p>Please copy or enter this code on the verification screen of <br/>your account registration to change password.</p>
            <h2>Verfication code: {verify_code}</h2>
        </body>
    </html>
    """


# Password_reset_request
@auth_bp.route("/reset_password", methods=["POST"])
def reset_password():
    email = request.json["email"]
    pin_code = request.json["pin_code"]
    new_password = request.json["new_password"]

    pass_code_obj = PassResetCode.query.filter_by(email=email).first()
    if not pass_code_obj:
        return jsonify({"message": "The user doesn't exist"}), 404

    print(pass_code_obj.pin_code)
    print(pin_code)
    if pass_code_obj.pin_code != pin_code:
        return jsonify({"message": "The verification code is invalid"}), 400

    if datetime.datetime.now() > pass_code_obj.expires_at:
        return jsonify({"message": "The verification code is expired"}), 400

    # Store new password to users table

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "The user doesn't exist"}), 404

    hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")
    user.password_hash = hashed_password
    try:
        db.session.commit()
    except IntegrityError as e:
        print(e)
        db.session.rollback()
        return (
            jsonify(message="Operation failed due to an unexpected error."),
            500,
        )
    except Exception as e:
        print(e)
        # Log the error 'e' or print it to the console
        return jsonify(message="Operation failed due to an unexpected error."), 500
    return jsonify(message="Password was successfully changed"), 200
