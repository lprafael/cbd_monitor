import { useEffect } from 'react';

/**
 * ChatBot Component
 * Integrates the n8n chat widget.
 * Using a safer dynamic approach to bypass react-scripts build limitations.
 */
const ChatBot = () => {
  useEffect(() => {
    if (window.n8nChatInitialized) return;
    window.n8nChatInitialized = true;

    // Inject advanced styles for a "Wow" effect
    const style = document.createElement('style');
    style.textContent = `
      :root {
        --sintra-primary: #0f172a;
        --sintra-accent: #10b981;
        --sintra-bg: #ffffff;
        --sintra-text: #1e293b;
      }
      
      .n8n-chat-widget {
        font-family: 'Outfit', 'Inter', sans-serif !important;
      }
      
      .n8n-chat-window {
        border-radius: 24px !important;
        box-shadow: 0 20px 50px -12px rgba(15, 23, 42, 0.25) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        backdrop-filter: blur(10px) !important;
        overflow: hidden !important;
        width: 400px !important;
        max-height: 700px !important;
      }

      /* Premium Header with Gradient */
      .n8n-chat-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
        padding: 24px 20px !important;
        border-bottom: none !important;
      }

      .n8n-chat-header-title {
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        font-size: 1.1rem !important;
      }

      .n8n-chat-header-subtitle {
        color: rgba(255, 255, 255, 0.7) !important;
        font-size: 0.85rem !important;
      }

      /* Modern Message Bubbles */
      .n8n-chat-message-text {
        border-radius: 18px !important;
        font-size: 0.95rem !important;
        line-height: 1.5 !important;
        padding: 12px 16px !important;
      }

      .n8n-chat-message-item.n8n-chat-message-from-bot .n8n-chat-message-text {
        background: #f1f5f9 !important;
        color: #1e293b !important;
        border-bottom-left-radius: 4px !important;
      }

      .n8n-chat-message-item.n8n-chat-message-from-user .n8n-chat-message-text {
        background: #10b981 !important;
        color: white !important;
        border-bottom-right-radius: 4px !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2) !important;
      }

      /* Sleek Input Area */
      .n8n-chat-input-container {
        padding: 20px !important;
        background: white !important;
        border-top: 1px solid #f1f5f9 !important;
      }

      .n8n-chat-input {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 14px !important;
        transition: all 0.3s ease !important;
        resize: none !important;
      }

      .n8n-chat-input:focus {
        background: white !important;
        border-color: #10b981 !important;
        box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.1) !important;
      }

      /* Animated Toggle Button */
      .n8n-chat-button {
        background: #0f172a !important;
        width: 60px !important;
        height: 60px !important;
        box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.4) !important;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
      }

      .n8n-chat-button:hover {
        transform: scale(1.1) rotate(5deg) !important;
      }

      /* Powered by hide (opcional para estética premium) */
      .n8n-chat-footer {
        display: none !important;
      }
    `;
    document.head.appendChild(style);

    const link = document.createElement('link');
    link.href = 'https://cdn.jsdelivr.net/npm/@n8n/chat/dist/style.css';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    const loadChat = new Function(`
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      const userEmpresa = localStorage.getItem('user_empresa') || '';
      // Nombre para saludo: nombre completo o username
      const userName = (user.nombre_completo && user.nombre_completo.trim()) ? user.nombre_completo.trim() : (user.username || '');
      // Metadata que N8N recibe en cada mensaje: nombre y empresa para personalizar saludos
      const metadata = {
        userName: userName,
        empresa: userEmpresa
      };

      // Usar el email si existe, sino un ID aleatorio persistente
      let sessionId = localStorage.getItem('sintra_chat_session');
      if (!sessionId) {
        sessionId = user.email || ('session_' + Math.random().toString(36).substring(2, 11));
        localStorage.setItem('sintra_chat_session', sessionId);
      }

      return import('https://cdn.jsdelivr.net/npm/@n8n/chat/dist/chat.bundle.es.js')
        .then(({ createChat }) => {
          createChat({
            webhookUrl: 'https://sistemas.mopc.gov.py/cbd_monitor/n8n/webhook/081df528-5853-456b-8c51-6c6dc9618940/chat',
            mode: 'window',
            showWelcomeScreen: true,
            sessionId: sessionId, // <--- Aquí pasamos el ID para mantener la memoria
            metadata: metadata, // userName y empresa para que el chatbot salude por nombre y tenga contexto de empresa
            i18n: {
              en: {
                title: 'SINTRA 👋',
                subtitle: 'Inteligenia de Transporte MOPC',
                inputPlaceholder: 'Escribe tu consulta aquí...',
                getStarted: 'Comenzar ahora',
              }
            },
            initialMessages: [
              userName ? ('👋 ¡Hola ' + userName + '! Soy **SINTRA**.') : '👋 ¡Hola! Soy **SINTRA**.',
              'Mantengo el contexto de nuestra última charla. ¿En qué más puedo ayudarte?'
            ],
            theme: {
              primaryColor: '#0f172a',
              secondaryColor: '#10b981',
            }
          });
        });
    `);

    loadChat().catch(err => {
      console.error('Error loading n8n ChatBot:', err);
    });
  }, []);

  return null;
};

export default ChatBot;
