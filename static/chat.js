// chat.js - Script per la chat riutilizzabile in tutte le pagine

function initChat(leagueCode, currentUserId, memberColors) {
  const chatMessages = document.getElementById("chat-messages");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatFloat = document.getElementById("chat-float");
  const chatBtn = document.getElementById("toggle-chat");
  const chatBadge = document.getElementById("chat-badge");
  const sendBtn = document.getElementById("send-btn");
  const attachBtn = document.querySelector(".attach-btn");
  const fileInput = document.getElementById("file-input");

  let lastSeenMessageId = null;
  let unreadCount = 0;
  let selectedFiles = [];

  // ===== UTILITY FUNCTIONS =====
  function updateButtonsVisibility() {
    sendBtn.disabled = chatInput.value.trim() === '';
  }

  function updateBadge() {
    chatBadge.style.display = unreadCount > 0 ? "inline" : "none";
    if (unreadCount > 0) chatBadge.textContent = unreadCount;
  }

  function getUserColor(username) {
    return memberColors[username] || '#333333';
  }

  // ===== CHAT FUNCTIONS =====
  function loadMessages() {
    fetch('/league/' + leagueCode + '/chat')
      .then(res => res.json())
      .then(messages => {
        chatMessages.innerHTML = '';
        messages.forEach(m => {
          const userColor = getUserColor(m.user);
          let content = '<strong style="color: ' + userColor + ';">' + m.user + '</strong>: <span style="color: #222;">' + m.message + '</span>';
          
          if (m.attachments && m.attachments.length > 0) {
            content += '<div class="attachments">';
            m.attachments.forEach(att => {
              if (att.type === 'image') {
                content += '<img src="' + att.url + '" style="max-width:200px;border-radius:8px;margin-top:5px;">';
              } else if (att.type === 'audio') {
                content += '<audio controls style="margin-top:5px;"><source src="' + att.url + '"></audio>';
              } else {
                content += '<a href="' + att.url + '" download style="display:block;margin-top:5px;">📎 ' + att.name + '</a>';
              }
            });
            content += '</div>';
          }
          
          chatMessages.innerHTML += '<div style="background:#f5f5f5;padding:8px;margin:5px;border-radius:8px;border-left: 3px solid ' + userColor + ';">' +
            content +
            '<span style="font-size:0.8em;color:#999;margin-left:8px;">' + new Date(m.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) + '</span>' +
          '</div>';
        });
        if(messages.length > 0) lastSeenMessageId = messages[messages.length - 1].id;
        unreadCount = 0;
        updateBadge();
        chatMessages.scrollTop = chatMessages.scrollHeight;
      })
      .catch(error => console.error('Errore:', error));
  }

  function sendMessage() {
    const msg = chatInput.value.trim();
    if(!msg && selectedFiles.length === 0) return;
    
    const formData = new FormData();
    formData.append('message', msg);
    selectedFiles.forEach((file, index) => formData.append('file_' + index, file));
    
    fetch('/league/' + leagueCode + '/chat', {
      method: "POST",
      body: formData
    })
    .then(res => res.json())
    .then(() => {
      chatInput.value = '';
      chatInput.style.height = 'auto';
      selectedFiles = [];
      fileInput.value = '';
      updateButtonsVisibility();
      loadMessages();
    })
    .catch(error => alert('Errore: ' + error.message));
  }

  function checkNewMessages() {
    fetch('/league/' + leagueCode + '/chat')
      .then(res => res.json())
      .then(messages => {
        if(messages.length === 0) return;
        if(lastSeenMessageId === null) {
          lastSeenMessageId = messages[messages.length - 1].id;
          return;
        }
        const newMessages = messages.filter(m => m.id > lastSeenMessageId);
        if(newMessages.length > 0) {
          unreadCount += newMessages.length;
          updateBadge();
          lastSeenMessageId = messages[messages.length - 1].id;
        }
      })
      .catch(error => console.error('Errore:', error));
  }

  window.closeChat = function() { 
    chatFloat.style.display = "none";
  }

  // ===== EVENT LISTENERS =====
  chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    updateButtonsVisibility();
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
    if(chatFloat.style.display === "none" || chatFloat.style.display === "") {
      chatFloat.style.display = "block";
      unreadCount = 0;
      updateBadge();
      loadMessages();
    } else {
      chatFloat.style.display = "none";
    }
  };

  // ===== INITIALIZATION =====
  updateButtonsVisibility();

  // Check for new messages periodically
  setInterval(() => {
    if(chatFloat.style.display === "none" || chatFloat.style.display === "") {
      checkNewMessages();
    } else {
      loadMessages();
    }
  }, 4000);

  // Initialize lastSeenMessageId
  fetch('/league/' + leagueCode + '/chat')
    .then(res => res.json())
    .then(messages => {
      if(messages.length > 0) lastSeenMessageId = messages[messages.length - 1].id;
    })
    .catch(error => console.error('Errore:', error));
}