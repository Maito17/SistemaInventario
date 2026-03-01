<!-- static/chatbot_ia.js -->
(function() {
    // Función para obtener el token CSRF de las cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Crear el botón flotante
    var btn = document.createElement('button');
    btn.id = 'ia-chatbot-btn';
    btn.innerHTML = '🤖 IA Ventas';
    btn.style.position = 'fixed';
    btn.style.bottom = '32px';
    btn.style.right = '32px';
    btn.style.zIndex = '9999';
    btn.style.background = 'linear-gradient(135deg, #6366f1, #8b5cf6)';
    btn.style.color = 'white';
    btn.style.border = 'none';
    btn.style.borderRadius = '50px';
    btn.style.padding = '16px 24px';
    btn.style.fontWeight = 'bold';
    btn.style.fontSize = '0.95rem';
    btn.style.boxShadow = '0 4px 15px rgba(99,102,241,0.4)';
    btn.style.cursor = 'pointer';
    btn.style.transition = 'transform 0.2s, box-shadow 0.2s';
    btn.onmouseenter = function() { btn.style.transform = 'scale(1.05)'; btn.style.boxShadow = '0 6px 20px rgba(99,102,241,0.5)'; };
    btn.onmouseleave = function() { btn.style.transform = 'scale(1)'; btn.style.boxShadow = '0 4px 15px rgba(99,102,241,0.4)'; };
    document.body.appendChild(btn);

    // Crear el chat flotante (oculto por defecto)
    var chat = document.createElement('div');
    chat.id = 'ia-chatbot-box';
    chat.style.position = 'fixed';
    chat.style.bottom = '90px';
    chat.style.right = '32px';
    chat.style.width = '380px';
    chat.style.maxHeight = '520px';
    chat.style.background = 'white';
    chat.style.borderRadius = '18px';
    chat.style.boxShadow = '0 8px 32px rgba(0,0,0,0.18)';
    chat.style.display = 'none';
    chat.style.flexDirection = 'column';
    chat.style.overflow = 'hidden';
    chat.style.zIndex = '9998';
    chat.innerHTML = `
        <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;padding:16px 20px;font-weight:bold;font-size:1.1rem;display:flex;align-items:center;justify-content:space-between;">
            <span>🤖 IA Ventas — Tu Negocio</span>
            <span id="ia-chatbot-close" style="cursor:pointer;font-size:1.4rem;opacity:0.8;transition:opacity 0.2s;" onmouseenter="this.style.opacity='1'" onmouseleave="this.style.opacity='0.8'">&times;</span>
        </div>
        <div id="ia-chatbot-suggestions" style="padding:10px 14px 4px;background:#f8fafc;display:flex;flex-wrap:wrap;gap:6px;">
            <button class="ia-suggest-btn" data-q="¿Cómo van mis ventas hoy?" style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:20px;padding:5px 12px;font-size:0.8rem;cursor:pointer;color:#4338ca;transition:background 0.2s;">📊 Ventas de hoy</button>
            <button class="ia-suggest-btn" data-q="¿Cuáles son mis productos más vendidos este mes?" style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:20px;padding:5px 12px;font-size:0.8rem;cursor:pointer;color:#4338ca;transition:background 0.2s;">🏆 Top productos</button>
            <button class="ia-suggest-btn" data-q="¿Tengo productos con stock bajo o por caducar?" style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:20px;padding:5px 12px;font-size:0.8rem;cursor:pointer;color:#4338ca;transition:background 0.2s;">⚠️ Alertas stock</button>
            <button class="ia-suggest-btn" data-q="¿Cuál es mi ganancia del mes y cómo se compara con el mes anterior?" style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:20px;padding:5px 12px;font-size:0.8rem;cursor:pointer;color:#4338ca;transition:background 0.2s;">💰 Rentabilidad</button>
            <button class="ia-suggest-btn" data-q="¿Tengo clientes inactivos que debería recuperar?" style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:20px;padding:5px 12px;font-size:0.8rem;cursor:pointer;color:#4338ca;transition:background 0.2s;">👥 Clientes</button>
            <button class="ia-suggest-btn" data-q="¿Cuánto me deben en créditos pendientes?" style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:20px;padding:5px 12px;font-size:0.8rem;cursor:pointer;color:#4338ca;transition:background 0.2s;">📋 Créditos</button>
        </div>
        <div id="ia-chatbot-messages" style="padding:14px;flex:1;min-height:200px;max-height:300px;overflow-y:auto;font-size:0.95rem;background:#f8fafc;line-height:1.5;"></div>
        <form id="ia-chatbot-form" style="display:flex;padding:12px;background:#f3f4f6;gap:8px;border-top:1px solid #e5e7eb;">
            <input id="ia-chatbot-input" type="text" placeholder="Pregunta sobre tu negocio..." style="flex:1;padding:10px 14px;border-radius:12px;border:1px solid #d1d5db;outline:none;font-size:0.95rem;transition:border 0.2s;" onfocus="this.style.borderColor='#6366f1'" onblur="this.style.borderColor='#d1d5db'" required />
            <button type="submit" id="ia-chatbot-send" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;border:none;border-radius:12px;padding:10px 18px;font-weight:bold;cursor:pointer;transition:opacity 0.2s;">Enviar</button>
        </form>
    `;
    document.body.appendChild(chat);

    // Mostrar/ocultar chat
    btn.onclick = function() {
        chat.style.display = chat.style.display === 'none' ? 'flex' : 'none';
    };
    chat.querySelector('#ia-chatbot-close').onclick = function() {
        chat.style.display = 'none';
    };

    // Función para formatear la respuesta (Markdown básico)
    function formatResponse(text) {
        // Negritas
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Listas con viñetas
        text = text.replace(/^\* (.+)$/gm, '<li style="margin-left:16px;">$1</li>');
        text = text.replace(/^- (.+)$/gm, '<li style="margin-left:16px;">$1</li>');
        // Saltos de línea
        text = text.replace(/\n/g, '<br>');
        return text;
    }

    // Función para enviar pregunta
    function enviarPregunta(pregunta) {
        var messages = chat.querySelector('#ia-chatbot-messages');
        var input = chat.querySelector('#ia-chatbot-input');
        var sendBtn = chat.querySelector('#ia-chatbot-send');
        var suggestions = chat.querySelector('#ia-chatbot-suggestions');

        if (!pregunta) return;

        // Ocultar sugerencias después del primer mensaje
        if (suggestions) suggestions.style.display = 'none';

        messages.innerHTML += `<div style='margin-bottom:10px;padding:8px 12px;background:#eef2ff;border-radius:12px;border-bottom-right-radius:4px;max-width:85%;margin-left:auto;'><strong style="color:#4338ca;">Tú:</strong> ${pregunta}</div>`;
        input.value = '';
        sendBtn.disabled = true;
        sendBtn.style.opacity = '0.6';
        messages.innerHTML += `<div id='ia-typing' style='color:#6366f1;margin-bottom:10px;padding:8px 12px;font-style:italic;'>
            <span class="ia-dots">⏳ Analizando datos de tu negocio</span>
        </div>`;
        messages.scrollTop = messages.scrollHeight;

        fetch('/api/ia-ventas/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({pregunta: pregunta})
        })
        .then(r => r.json())
        .then(data => {
            var typing = document.getElementById('ia-typing');
            if (typing) typing.remove();
            sendBtn.disabled = false;
            sendBtn.style.opacity = '1';
            if (data.respuesta) {
                messages.innerHTML += `<div style='margin-bottom:12px;padding:10px 14px;background:white;border-radius:12px;border-bottom-left-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,0.08);max-width:90%;line-height:1.6;'><strong style="color:#6366f1;">🤖 IA:</strong><br>${formatResponse(data.respuesta)}</div>`;
            } else {
                messages.innerHTML += `<div style='color:#dc2626;margin-bottom:12px;padding:10px 14px;background:#fef2f2;border-radius:12px;'><strong>❌ Error:</strong> ${data.error || 'No se pudo obtener respuesta.'}</div>`;
            }
            messages.scrollTop = messages.scrollHeight;
        })
        .catch(() => {
            var typing = document.getElementById('ia-typing');
            if (typing) typing.remove();
            sendBtn.disabled = false;
            sendBtn.style.opacity = '1';
            messages.innerHTML += `<div style='color:#dc2626;margin-bottom:12px;padding:10px 14px;background:#fef2f2;border-radius:12px;'><strong>❌ Error:</strong> Error de conexión con el servidor.</div>`;
            messages.scrollTop = messages.scrollHeight;
        });
    }

    // Manejar envío del formulario
    var form = chat.querySelector('#ia-chatbot-form');
    var input = chat.querySelector('#ia-chatbot-input');
    form.onsubmit = function(e) {
        e.preventDefault();
        enviarPregunta(input.value.trim());
    };

    // Manejar botones de sugerencia
    chat.querySelectorAll('.ia-suggest-btn').forEach(function(suggestBtn) {
        suggestBtn.onclick = function() {
            enviarPregunta(this.getAttribute('data-q'));
        };
    });
})();
