// Firebase Messaging service worker for web push notifications.
// Receives background push messages when the buddy web app is not in focus.

importScripts('https://www.gstatic.com/firebasejs/11.0.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.0.2/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyBackbuyxigadeECvtELU9hOhUH0RfJffU",
  authDomain: "disconnect-5cf11.firebaseapp.com",
  projectId: "disconnect-5cf11",
  storageBucket: "disconnect-5cf11.firebasestorage.app",
  messagingSenderId: "994480224851",
  appId: "1:994480224851:web:7589bb5f946afd9e8ee4a6",
});

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage(function(payload) {
  const { title, body } = payload.notification || {};
  const data = payload.data || {};

  // Deep-link click into the buddy dashboard
  const clickAction = '/buddy/' + (data.request_id ? '?request=' + data.request_id : '');

  self.registration.showNotification(title || 'Disconnect', {
    body: body || 'Someone needs your approval.',
    icon: '/favicon-192.png',
    badge: '/favicon-32.png',
    data: { clickAction },
  });
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.clickAction) || '/buddy/';
  event.waitUntil(clients.openWindow(url));
});
