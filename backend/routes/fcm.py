import os
import json

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    from firebase_admin.exceptions import FirebaseError
    
    service_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if service_json and not firebase_admin._apps:
        try:
            cred_dict = json.loads(service_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin initialized for push")
        except Exception as e:
            print(f"Firebase Admin parse error: {e}")
    firebase_ready = len(firebase_admin._apps) > 0 if 'firebase_admin' in locals() else False
except Exception as e:
    print(f"Firebase Admin not installed: {e}")
    firebase_admin = None
    firebase_ready = False

def _get_tokens_query():
    from models import FCMToken
    return FCMToken

def send_push_to_tokens(tokens, title, body, link="/shop.html"):
    if not firebase_ready or not tokens:
        print(f"Push skipped: ready={firebase_ready}, tokens={len(tokens) if tokens else 0}")
        return 0
    success = 0
    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={"link": link},
                token=token
            )
            messaging.send(message)
            success += 1
        except Exception as e:
            print(f"Push fail {token[:15]}: {e}")
    print(f"✅ Push sent {success}/{len(tokens)}")
    return success

def send_push_to_all(title, body, link="/shop.html"):
    try:
        FCMToken = _get_tokens_query()
        tokens = [t.token for t in FCMToken.query.all()]
        return send_push_to_tokens(tokens, title, body, link)
    except Exception as e:
        print(f"send_push_to_all error: {e}")
        return 0

def send_push_to_user(user_id, title, body, link="/shop.html"):
    try:
        FCMToken = _get_tokens_query()
        tokens = [t.token for t in FCMToken.query.filter_by(user_id=user_id).all()]
        # fallback: if user has no token, send to all admins (at least you get it)
        if not tokens:
            tokens = [t.token for t in FCMToken.query.all()]
        return send_push_to_tokens(tokens, title, body, link)
    except Exception as e:
        print(f"send_push_to_user error: {e}")
        return 0
