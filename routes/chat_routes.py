from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
import datetime
import requests
import uuid

chat_bp = Blueprint("chat_bp", __name__)

from models import User, Invitation, Friend, db
from config import ApplicationConfig

OPENAI_KEY = ApplicationConfig.OPENAI_KEY
PINECONE_API_KEY = ApplicationConfig.PINECONE_API_KEY
PINECONE_ENV = ApplicationConfig.PINECONE_ENV


# Upload user's avatar
@chat_bp.route("/invite", methods=["POST"])
def friend_invite():
    # user_id = request.json["from_id"]
    # friend_email = request.json["friend_email"]

    user_id = "4db2a948-61c2-4578-836f-0f688f2aedac"
    friend_email = "a@a.com"

    # check if user_id is invalid
    user_obj = User.query.get(user_id)
    if not user_obj:
        return jsonify(message="The user id is not valid"), 400

    username = user_obj.username
    if not username:
        username = user_obj.email

    # check if friend email is invalid
    friend_user_obj = User.query.filter_by(email=friend_email).first()
    if not friend_user_obj:
        return jsonify(message="The friend email is not found"), 404

    friend_user_id = str(friend_user_obj.id)
    print(user_id)
    print(friend_user_id)

    friend_obj = Friend.query.get({"user_id": user_id, "friend_id": friend_user_id})

    # check if provided friend is not in the user's friend list.
    if not friend_obj:
        return jsonify(message="The selected user is not in the friend list"), 404

    # We also should be aware of ```Status```` variable

    # Add new invitation to the table
    unique_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
    new_invite_obj = Invitation(
        id=unique_id,
        from_id=user_id,
        to_email=friend_email,
        token=token,
        status=1,
        expires_at=expires_at,
    )
    db.session.add(new_invite_obj)
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

    # Send message to friend's email
    response = send_invitation_email(username, friend_email, token)
    return (
        jsonify({"message": f"Invitation email is sent to the {friend_email}'s email"}),
        200,
    )


def send_invitation_email(from_name, email, token):
    return requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": f"Dood Team <mail@{MAILGUN_DOMAIN}>",
            "to": [email],
            "subject": f"You received an invitation to collaborate",
            "html": invitation_email_template(from_name, token),
        },
    )


def invitation_email_template(from_name, token):
    return f"""
    <html>
        <body style='text-align: center'>
            <h1>You received an invitation to collaborate</h1>
            <p>{from_name} just sent you an invite to collaborate in AIOChat. Click the button below to <br/>collaborate. Otherwise, please ignore or delete this email if it is a mistake.</p>
            <h2><a href="/join?token={token}">Let's collaborate!</h2>
        </body>
    </html>
    """


@chat_bp.route("/join?token=<token>", methods=["POST"])
def join_chat(token):
    # conn = get_db_connection()
    # cur = conn.cursor()
    # invitation = cur.execute(f"SELECT * FROM invitations WHERE token='{token}'")
    # row = cur.fetchone()
    # print(row)
    # # conn.commit()
    # cur.close()
    # conn.close()

    # if row and datetime.datetime.now() < row[1]:
    #     # Token is valid and not expired
    #     return "Welcome to the chat room!"
    # else:
    #     # Token is expired or invalid
    #     return redirect(url_for("login_user"))
    return True
