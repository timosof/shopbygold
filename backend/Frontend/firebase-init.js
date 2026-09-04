// firebase-init.js - loads on every page
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getMessaging, getToken, onMessage } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging.js";

const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "shopbygold.firebaseapp.com",
  projectId: "shopbygold",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

// Save token on every page load
if ('Notification' in window) {
  Notification.requestPermission().then(permission => {
    if (permission === 'granted') {
      getToken(messaging, { vapidKey: 'YOUR_VAPID_KEY' }).then(token => {
        if (token) {
          localStorage.setItem('fcm_token', token);
          fetch('/api/save-fcm-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token })
          }).then(()=>console.log("Token saved:", token));
        }
      });
    }
  });

  // Show push when user is on any page
  onMessage(messaging, (payload) => {
    console.log("Push received:", payload);
    if (Notification.permission === 'granted') {
      new Notification(payload.notification.title, {
        body: payload.notification.body,
        icon: '/icon.png'
      });
    }
  });
}
