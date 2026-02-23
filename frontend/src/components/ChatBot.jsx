import React, { useState, useEffect, useRef } from 'react';
import './ChatBot.css';

const ChatBot = ({ knowledgeFileUrl }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { text: '¡Hola! Soy SINTRA (Sistema Inteligente de Normativa de Transporte). ¿En qué puedo ayudarte hoy con la normativa de transporte?', sender: 'bot' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [knowledgeBase, setKnowledgeBase] = useState('');
  const [currentTopic, setCurrentTopic] = useState(null); // 'ifo', 'cbd', 'sanciones'
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // En una implementación real, esto vendría de un backend con RAG/LLM
  // Para este prototipo, simulamos una búsqueda en el archivo de conocimiento
  useEffect(() => {
    const fetchKnowledge = async () => {
      try {
        // Intentamos cargar el archivo de normativa
        const response = await fetch('/especificacion_completa_resolucion_2025.md');
        if (response.ok) {
          const text = await response.text();
          setKnowledgeBase(text);
        }
      } catch (error) {
        console.error('Error cargando base de conocimientos:', error);
      }
    };
    fetchKnowledge();
  }, []);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMessage = { text: inputValue, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    // Simular procesamiento del bot
    setTimeout(() => {
      const botResponse = generateResponse(inputValue);
      setMessages(prev => [...prev, { text: botResponse, sender: 'bot' }]);
      setLoading(false);
    }, 1000);
  };

  const generateResponse = (query) => {
    const q = query.toLowerCase();

    // Identificar Tópico Principal (Actualizar contexto)
    let topic = currentTopic;
    if (q.includes('ifo') || q.includes('flota operativa')) topic = 'ifo';
    else if (q.includes('cbd') || q.includes('cantidad mínima') || q.includes('buses diferentes')) topic = 'cbd';
    else if (q.includes('sanción') || q.includes('multa') || q.includes('penalización') || q.includes('sancion')) topic = 'sanciones';
    else if (q.includes('clima') || q.includes('lluvia') || q.includes('precipitaciones')) topic = 'clima';
    else if (q.includes('redondeo') || q.includes('decimal')) topic = 'redondeo';

    setCurrentTopic(topic);

    // Manejo de quejas del usuario
    if (q.includes('respondiendo lo mismo') || q.includes('misma cosa') || q.includes('no tiene lógica')) {
      return 'Lamento que mi respuesta anterior no haya sido útil. Intentaré ser más específico. ¿Te gustaría conocer la fórmula matemática del CBD, los niveles de sanción o los ajustes por feriados?';
    }

    // FÓRMULAS (Check prioritario)
    if (q.includes('fórmula') || q.includes('formula') || q.includes('cálculo') || q.includes('calcula')) {
      if (topic === 'cbd') {
        return 'La fórmula del ICCBDM (Cumplimiento de CBD) es: (0.70 × IH_franja) + (0.30 × IF_franja). Donde IH es el promedio de cumplimiento horario y IF es el cumplimiento por franja. Ninguna hora puede ser inferior al CBDmín oficial.';
      }
      if (topic === 'ifo') {
        return 'La fórmula del IFO Hora es: (Buses Observados / Media de Buses Días Equivalentes) × 100. Recuerda que para meses atípicos como enero o diciembre, el denominador se multiplica por un factor de 0.80.';
      }
      return '¿Sobre qué fórmula deseas consultar? Tengo información detallada del IFO (Flota Operativa) y del ICCBDM (Mínimo de Buses).';
    }

    // CÓMO SE MIDE
    if (q.includes('cómo se mide') || q.includes('como se mide') || q.includes('por hora') || q.includes('franja')) {
      if (topic === 'cbd') {
        return 'El CBDmín se mide en dos niveles: 1. Por hora reloj (donde fallar una hora ya es infracción intermedia) y 2. Por franja operativa (donde es infracción grave). No se compensan buses entre horas.';
      }
      if (topic === 'ifo') {
        return 'El IFO se mide comparando los buses diferentes actuales vs el promedio de buses en días similares del pasado (días equivalentes). Se calcula por hora, por franja, diario y mensual.';
      }
    }

    // MÉTRICAS GENERALES
    if (q.includes('métricas') || q.includes('metricas') || q.includes('que se controla')) {
      return 'Las métricas clave son: IFO (Índice de Flota Operativa), CBDmín (Cantidad Mínima de Buses Diferentes) e ICF (Frecuencia). ¿Te gustaría profundizar en alguna de ellas?';
    }

    // TOPIC FALLBACKS (Más específicos que antes)
    if (topic === 'ifo') {
      return 'El IFO (Índice de Flota Operativa) mide el rendimiento de tu flota respecto a su propio historial. ¿Quieres saber sobre los ajustes por clima de la DINAC o sobre cómo se calculan los días feriados?';
    }

    if (topic === 'cbd') {
      return 'El CBDmín es el "mínimo vital" de buses. Por ejemplo, en horas Pico se exigen al menos 12 buses diferentes. No se permiten reducciones por lluvia. ¿Consultarías la fórmula de cumplimiento?';
    }

    if (topic === 'sanciones') {
      return 'Las sanciones según la Resolución 120/2025: Gravísima (173 jornales si fallas en el IFO Mensual), Grave (Infracción de CBD por franja) e Intermedia (20 jornales). ¿Quieres saber de alguna específica?';
    }

    if (topic === 'redondeo') {
      return 'La regla de oro actual es: todos los cálculos se redondean a **dos dígitos decimales** (Res. 2026).';
    }

    // SALUDOS
    if (q.includes('hola') || q.includes('buenos días') || q.includes('buenas tardes')) {
      return '¡Hola! Soy SINTRA. Estoy aquí para resolver tus dudas sobre la Resolución GVMT 120/2025. ¿En qué puedo ayudarte?';
    }

    return 'Entiendo tu consulta. Como experto en la normativa 120/2025, puedo darte detalles técnicos de las fórmulas o los niveles de servicio. ¿Deseas ser más específico sobre IFO o CBD?';
  };

  return (
    <div className={`sintra-chatbot-container ${isOpen ? 'open' : ''}`}>
      {!isOpen && (
        <button className="sintra-launcher" onClick={() => setIsOpen(true)} title="SINTRA - Consultar Normativa">
          <img src="/imagenes/SINTRA.png" alt="SINTRA" className="sintra-logo-img" />
          <span className="sintra-badge">SINTRA</span>
        </button>
      )}

      {isOpen && (
        <div className="sintra-window">
          <div className="sintra-header">
            <div className="sintra-header-info">
              <img src="/imagenes/SINTRA.png" alt="SINTRA" className="sintra-logo-mini" />
              <div>
                <h3>SINTRA</h3>
                <span>Normativa de Transporte</span>
              </div>
            </div>
            <button className="sintra-close" onClick={() => setIsOpen(false)}>×</button>
          </div>

          <div className="sintra-messages">
            {messages.map((msg, index) => (
              <div key={index} className={`sintra-message ${msg.sender}`}>
                <div className="message-bubble">{msg.text}</div>
              </div>
            ))}
            {loading && (
              <div className="sintra-message bot">
                <div className="message-bubble typing">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="sintra-input-area" onSubmit={handleSendMessage}>
            <input
              type="text"
              placeholder="Escribe tu consulta..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading || !inputValue.trim()}>
              <svg viewBox="0 0 24 24" width="24" height="24">
                <path fill="currentColor" d="M2.01 21L23 12L2.01 3L2 10l15 2l-15 2z" />
              </svg>
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default ChatBot;
