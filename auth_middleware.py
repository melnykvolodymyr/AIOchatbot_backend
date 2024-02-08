from flask import request, jsonify
from config import ApplicationConfig
import jwt
import datetime

SECRET_KEY = ApplicationConfig.SECRET_KEY


def verify_token(token):
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload  # or return True if you just need to verify
    except jwt.ExpiredSignatureError:
        # Token has expired
        return None
    except jwt.InvalidTokenError:
        # Token is invalid
        return None


def token_required(f):
    def decorator(*args, **kwargs):
        # Get the token from the headers
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        # The token normally comes with the text 'Bearer ' prefix
        # Remove it to get the actual token
        if "Bearer " in token:
            token = token.replace("Bearer ", "")

        # Verify the token
        if not verify_token(token):
            return jsonify({"message": "Token is invalid!"}), 401

        return f(*args, **kwargs)

    decorator.__name__ = f.__name__
    return decorator


def encode_auth_token(user_id):
    try:
        # Create the access token
        access_token_payload = {
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            "iat": datetime.datetime.utcnow(),
            "sub": user_id,
        }
        access_token = jwt.encode(access_token_payload, SECRET_KEY, algorithm="HS256")

        # Create the refresh token
        refresh_token_payload = {
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1),
            "iat": datetime.datetime.utcnow(),
            "sub": user_id,
        }
        refresh_token = jwt.encode(refresh_token_payload, SECRET_KEY, algorithm="HS256")

        return {"access_token": access_token, "refresh_token": refresh_token}
    except Exception as e:
        return e


def decode_auth_token(auth_token):
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        return "Signature expired. Please log in again."
    except jwt.InvalidTokenError:
        return "Invalid token. Please log in again."
