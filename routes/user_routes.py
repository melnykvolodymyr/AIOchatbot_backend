from flask import Blueprint, request, jsonify, current_app
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from google.cloud import storage
from google.oauth2 import service_account
import datetime
import string
import secrets
import uuid
import requests

from models import User, EmailConfirmCode, PassResetCode, Friend, db
from config import ApplicationConfig

# Get MailGun information from config
MAILGUN_DOMAIN = ApplicationConfig.MAILGUN_DOMAIN
MAILGUN_API_KEY = ApplicationConfig.MAILGUN_API_KEY

# Added service account
storage_client = storage.Client.from_service_account_json("./credential.json")

user_bp = Blueprint("user_bp", __name__)

bcrypt = Bcrypt()


def model_to_dict(obj):
    # Dictionary comprehension to filter out SQLAlchemy-specific attributes
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


# Get User Data
@user_bp.route("/<user_id>", methods=["GET"])
def get_user_by_id(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify(message="User not found"), 404
    user_dict = model_to_dict(user)
    return jsonify(user_dict)


# Update User Data
@user_bp.route("/<user_id>", methods=["PATCH"])
def update_user_by_id(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify(message="User not found"), 404

    update_fields = request.json
    allowed_update_fields = {"username", "email"}  # Add your fields here

    for field, value in update_fields.items():
        if field in allowed_update_fields:
            setattr(user, field, value)
    print("@@@@@@@@@")
    print(user)
    print("@@@@@@@@@")
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

    return (
        jsonify({"message": "User profile changed successfully"}),
        200,
    )  # serialize user object to JSON


# Delete User
@user_bp.route("/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify(message="User not found"), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify(message="User deleted successfully")


# Upload user's avatar
@user_bp.route("/<user_id>/upload_avatar", methods=["POST"])
def upload_avatar(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify(message="User not found"), 404

    file = request.files.get("avatar")
    if not file:
        return jsonify({"error": "Image is required"}), 400

    url = gcs_upload_image(file)
    if not url:
        return jsonify({"error": "Failed to upload image"}), 500

    user.avatar_url = url
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
    return jsonify(message="User avatar uploaded successfully"), 500


def gcs_upload_image(file):
    try:
        # bucket name is aio-stage-assets
        bucket = storage_client.get_bucket("aio-stage-assets")
        destination_blob_name = str(uuid.uuid4())
        blob = bucket.blob("avatars/" + destination_blob_name)

        # Use upload_from_file instead of upload_from_filename
        blob.upload_from_file(file.stream, content_type=file.content_type)
        print(f"File uploaded to {destination_blob_name}.")

        # Generate the file URL if needed
        file_url = (
            blob.public_url
        )  # Adjust as needed based on your bucket's access policies
        return file_url
    except Exception as e:
        print(f"Failed to upload file: {e}")
        return False

# Email confirmation request
@user_bp.route("/send_confirmation", methods=["POST"])
def send_confirm_request():
    email = request.json["email"]
    user = User.query.filter_by(email=email).first()
    if not user:
        return (
            jsonify(message="The user doesn't exist"),
            400,
        )
    email_code_obj = EmailConfirmCode.query.filter_by(email=email).first()

    # Generate password reset code
    pin_code = generate_email_confirm_code()

    # Store infomation in table
    unique_id = str(uuid.uuid4())
    expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
    if email_code_obj:
        email_code_obj.pin_code = pin_code
        email_code_obj.expires_at = expires_at
        db.session.commit()
    else:
        new_confirm_code = EmailConfirmCode(
            id=unique_id, email=email, pin_code=pin_code, expires_at=expires_at
        )
        db.session.add(new_confirm_code)
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
    response = send_email_confirm_email(email, pin_code)
    return jsonify({"message": "The verification code is sent to your email"}), 200


def generate_email_confirm_code(length=8):
    # Generate a secure random string for password reset
    characters = string.ascii_letters + string.digits
    reset_code = "".join(secrets.choice(characters) for i in range(length))
    return reset_code


def send_email_confirm_email(email, pin_code):
    return requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": f"Dood Team <mail@{MAILGUN_DOMAIN}>",
            "to": [email],
            "subject": f"Password verification code: {pin_code}",
            "html": email_confirm_email_template(pin_code),
        },
    timeout=60)


def email_confirm_email_template(verify_code):
    return f"""
    <html>
        <body style='text-align: center'>
            <h1>Complete Your Sign Up Process</h1>
            <p>Please copy or enter this code on the verification screen of <br/>your account registration to complete sign up process.</p>
            <h2>Verfication code: {verify_code}</h2>
        </body>
    </html>
    """


# Password_reset_request
@user_bp.route("/email_confirm", methods=["POST"])
def email_confirm():
    email = request.json["email"]
    pin_code = request.json["pin_code"]

    confirm_code_obj = EmailConfirmCode.query.filter_by(email=email).first()
    if not confirm_code_obj:
        return jsonify({"message": "The user doesn't exist"}), 404

    if confirm_code_obj.pin_code != pin_code:
        return jsonify({"message": "The verification code is invalid"}), 400

    if datetime.datetime.now() > confirm_code_obj.expires_at:
        return jsonify({"message": "The verification code is expired"}), 400

    # Store new password to users table

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "The user doesn't exist"}), 404

    user.email_verified_at = datetime.datetime.now()
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
    return jsonify(message="Your email was successfully verified"), 200


def isValidUser(user_id):
    user = User.query.get(user_id)
    if not user:
        return None
    return user


##############################################################################################################################
##############################################################################################################################
##############################################################################################################################
#                           Manage user's friend list
@user_bp.route("/friend/<user_id>", methods=["GET", "POST", "DELETE"])
def get_friend_list(user_id):
    if request.method == "GET":
        if isValidUser(user_id) is None:
            return jsonify(message="The userid is not valid"), 400
        friend_arr = Friend.query.filter_by(user_id=user_id)
        if not friend_arr:
            return jsonify({"message": "There is no friend"}), 404
        friends_list = [model_to_dict(friend) for friend in friend_arr]
        return jsonify(friend_list=friends_list), 200

    elif request.method == "POST":
        # if isValidUser(user_id) is None:
        #     return jsonify(message="The userid is not valid"), 400
        # friend_email = request.json["email"]
        friend_email = "a@a.com"

        friend_obj = User.query.filter_by(email=friend_email).first()
        if not friend_obj:
            return jsonify(message="The friend email is not valid"), 400

        friend_id = str(friend_obj.id)

        target_obj = Friend.query.filter_by(
            user_id=user_id, friend_id=friend_id
        ).first()
        if target_obj:
            return jsonify(message="The friend already is in list"), 400

        unique_id = str(uuid.uuid4())
        new_obj = Friend(
            id=unique_id,
            user_id=user_id,
            friend_id=friend_id,
            status=1,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )
        db.session.add(new_obj)
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
        return jsonify(message="The friend is successfully added to the list"), 200

    elif request.method == "DELETE":
        print("@@@@@@@@@@@@@@@@@@@")
        mode = request.args.get("mode", default=None, type=str)
        print("@@@@@@@@@: ", mode)
        if not isValidUser(user_id):
            return jsonify(message="The userid is not valid"), 400
        friend_email = request.json["friend_email"]
        print(friend_email)
        friend_obj = User.query.filter_by(email=friend_email).first()
        if not friend_obj:
            return jsonify(message="The friend email is not valid"), 400

        friend_id = str(friend_obj.id)
        print(friend_id)

        if mode == "single":
            target_obj = Friend.query.get(user_id=user_id, friend_id=friend_id)
            if not target_obj:
                return jsonify(message="The friend doesn't exist in list"), 400
            db.session.delete(target_obj)

        elif mode == "all":
            target_objs = Friend.query.filter_by(user_id=user_id, friend_id=friend_id)
            if not target_obj:
                return jsonify(message="The friend doesn't exist in list"), 400
            target_objs.delete()

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
        return jsonify(message="The friend delete operation was successfully done"), 200
