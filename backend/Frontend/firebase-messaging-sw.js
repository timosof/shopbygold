importScripts('https://www.gstatic.com/firebasejs/10.13.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.13.1/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyDpS6VQdXbgEhNyCpyvM7tnFezSIcTnpYs",
  authDomain: "shopbygold-b32af.firebaseapp.com",
  projectId: "shopbygold-b32af",
  storageBucket: "shopbygold-b32af.firebasestorage.app",
  messagingSenderId: "749710700838",
  appId: "1:749710700838:web:49051875f7891ef99611e7"
});

const messaging = firebase.messaging();
