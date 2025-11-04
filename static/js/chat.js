(function() {
  const pathMatch = window.location.pathname.match(/\/league\/([^\/]+)/);
  if (!pathMatch) {
    const container = document.getElementById('chat-container');
    if (container) container.style.display = 'none';
    return;
  }

  const leagueCode = pathMatch[1];
  const chatMessages = document.getElementById('chat-messages');
  const chatInput = document.getElementById('chat-input');
  const chatFloat = document.getElementById('chat-float');
  const chatBtn = document.getElementById('toggle-chat');
  const chatBadge = document.getElementById('chat-badge');
  const sendBtn = document.getElementById('send-btn');

  let lastSeenMessageId = null;
  let unreadCount = 0;
  let memberColors = {};

  function loadMemberColors() {
    fetch('/league/' + leagueCode + '/members-colors')
      .then(res => res.json())
      .then(data => { memberColors = data.colors || {}; })
      .catch(err => console.error('Errore colori:', err));
  }

  chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
  });

  chatInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', function(e) {
    e.preventDefault();
    sendMessage();
  });

  chatBtn.onclick = function() {
    if (chatFloat.style.display === 'none' || !chatFloat.style.display) {
      chatFloat.style.display = 'block';
      unreadCount = 0;
      updateBadge();
      loadMessages();
    } else {
      chatFloat.style.display = 'none';
    }
  };

  function updateBadge() {
    chatBadge.style.display = unreadCount > 0 ? 'inline' : 'none';
    if (unreadCount > 0) chatBadge.textContent = unreadCount;
  }

  function getUserColor(username) {
    return memberColors[username] || '#333';
  }

  function loadMessages() {
    fetch('/league/' + leagueCode + '/chat')
      .then(res => res.json())
      .then(messages => {
        chatMessages.innerHTML = '';
        messages.forEach(m => {
          const color = getUserColor(m.user);
          const time = new Date(m.created_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
          chatMessages.innerHTML += '<div style="background:#f5f5f5;padding:8px;margin:5px;border-radius:8px;border-left:3px solid '+color+';"><strong style="color:'+color+';">'+m.user+'</strong>: '+m.message+'<span style="font-size:0.8em;color:#999;margin-left:8px;">'+time+'</span></div>';
        });
        if (messages.length > 0) lastSeenMessageId = messages[messages.length - 1].id;
        unreadCount = 0;
        updateBadge();
        chatMessages.scrollTop = chatMessages.scrollHeight;
      })
      .catch(err => console.error('Errore caricamento:', err));
  }

  function sendMessage() {
    const msg = chatInput.value.trim();
    if (!msg) return;
    fetch('/league/' + leagueCode + '/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    })
    .then(res => res.json())
    .then(data => {
      chatInput.value = '';
      chatInput.style.height = 'auto';
      loadMessages();
    })
    .catch(err => alert('Errore: ' + err));
  }

  function checkNewMessages() {
    fetch('/league/' + leagueCode + '/chat')
      .then(res => res.json())
      .then(messages => {
        if (messages.length === 0 || lastSeenMessageId === null) {
          if (messages.length > 0) lastSeenMessageId = messages[messages.length - 1].id;
          return;
        }
        const newMessages = messages.filter(m => m.id > lastSeenMessageId);
        if (newMessages.length > 0) {
          unreadCount += newMessages.length;
          updateBadge();
          lastSeenMessageId = messages[messages.length - 1].id;
        }
      })
      .catch(err => console.error('Errore check:', err));
  }

  setInterval(() => {
    if (chatFloat.style.display === 'none' || !chatFloat.style.display) {
      checkNewMessages();
    } else {
      loadMessages();
    }
  }, 4000);

  loadMemberColors();
  loadMessages();
})();
