import { useEffect } from 'react';

/**
 * ChatBot Component
 * Integrates the n8n chat widget as requested.
 * Configured for SINTRA: Sistema Inteligente de Normativas de Transporte.
 */
const ChatBot = () => {
  useEffect(() => {
    // Avoid double initialization in development or upon re-renders
    if (window.n8nChatInitialized) return;
    window.n8nChatInitialized = true;

    // Load the required CSS for the n8n chat widget
    const link = document.createElement('link');
    link.href = 'https://cdn.jsdelivr.net/npm/@n8n/chat/dist/style.css';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    // Dynamic import of the chat bundle and implementation of the requested configuration
    const initChat = async () => {
      try {
        const { createChat } = await import('https://cdn.jsdelivr.net/npm/@n8n/chat/dist/chat.bundle.es.js');

        createChat({
          webhookUrl: 'http://172.16.222.222:5678/webhook/081df528-5853-456b-8c51-6c6dc9618940/chat',
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
            primaryColor: '#0f172a',   // Azul oscuro
            secondaryColor: '#22c55e', // Verde moderno
          }
        });
      } catch (error) {
        console.error('Error al cargar el script del ChatBot de n8n:', error);
      }
    };

    initChat();
  }, []);

  // The chat widget is injected into the body by the n8n library
  return null;
};

export default ChatBot;
