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

    const link = document.createElement('link');
    link.href = 'https://cdn.jsdelivr.net/npm/@n8n/chat/dist/style.css';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    // Using new Function to hide dynamic import from the Webpack/react-scripts compiler
    const loadChat = new Function(`
      return import('https://cdn.jsdelivr.net/npm/@n8n/chat/dist/chat.bundle.es.js')
        .then(({ createChat }) => {
          createChat({
            webhookUrl: window.location.origin + '/cbd_monitor/n8n/webhook/081df528-5853-456b-8c51-6c6dc9618940/chat',
            i18n: {
              en: {
                title: '¡Hola! 👋',
                subtitle: 'SINTRA: Sistema Inteligente de Normativas de Transporte',
                inputPlaceholder: 'Escribí tu mensaje...',
                getStarted: 'Iniciar conversación',
              }
            },
            initialMessages: [
              '👋 ¡Hola! Soy SINTRA: Sistema Inteligente de Normativas de Transporte.',
              '💻 ¿En qué puedo ayudarte hoy?'
            ],
            theme: {
              primaryColor: '#0f172a',
              secondaryColor: '#22c55e',
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
