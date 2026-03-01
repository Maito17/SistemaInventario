function showErrorMessage(message, isPersistent = false) {
    const errorMessageDiv = document.getElementById('errorMessage');
    const errorTextSpan = document.getElementById('errorText');
    const djangoErrorMessage = document.getElementById('djangoErrorMessage');

    // 1. Asegurarse de que el div de error exista
    if (!errorMessageDiv || !errorTextSpan) {
        console.error("Elementos de error no encontrados en el DOM.");
        return;
    }

    // Ocultar el error de Django si existe
    if (djangoErrorMessage) djangoErrorMessage.style.display = 'none';

    errorTextSpan.textContent = message;
    
    // 2. MOSTRAR: Remover la clase 'hidden' de Tailwind para hacerlo visible
    errorMessageDiv.classList.remove('hidden'); 

    // Agitar el formulario para llamar la atención
    const form = document.getElementById('authForm');
    if (form) {
        form.classList.add('shake');
        setTimeout(() => form.classList.remove('shake'), 500);
    } else {
        console.warn("Advertencia: No se encontró el elemento con ID 'authForm' para el efecto de agitar.");
    }

    // 3. OCULTAR: Añadir la clase 'hidden' para ocultar automáticamente si no es persistente
    if (!isPersistent) {
        setTimeout(() => {
            errorMessageDiv.classList.add('hidden'); // Usa add('hidden') para ocultar
        }, 5000);
    }
}

// Función de utilidad para ocultar errores
function hideErrorMessage() {
    const errorMessageDiv = document.getElementById('errorMessage');
    if (errorMessageDiv) {
        errorMessageDiv.classList.add('hidden');
    }
}


// Función de utilidad para mostrar el modal de éxito (Se mantiene por si Django lo activa)
function showSuccessModal(message) {
    const successModal = document.getElementById('successModal');
    // Usamos el mismo display para mostrar un mensaje general de éxito
    document.getElementById('userUidDisplay').textContent = message; 
    successModal.classList.remove('hidden');
}


// Función principal que inicia la aplicación
function setupApp() {
    const form = document.getElementById('authForm'); 
    const submitBtn = document.getElementById('submitBtn');
    const actionText = document.getElementById('actionText');
    const loadingIcon = document.getElementById('loadingIcon');
    const successModal = document.getElementById('successModal');
    const closeModal = document.getElementById('closeModal');
    const togglePassword = document.getElementById('togglePassword');
    const eyeIcon = document.getElementById('eyeIcon');
    const toggleModeBtn = document.getElementById('toggleModeBtn');
    const formTitle = document.getElementById('formTitle'); 
    const formSubtitle = document.getElementById('formSubtitle');

    let isLoginMode = true; // Estado para alternar entre Login y Registro

    // ----------------------------------------------------
    // 1. Manejador para mostrar/ocultar contraseña
    // ----------------------------------------------------
    if (togglePassword) {
        togglePassword.addEventListener('click', function (e) {
            createRipple(e); // Efecto visual
            const passwordInput = document.getElementById('password');
            if (!passwordInput) return;
            
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);

            eyeIcon.style.transform = 'scale(0.8)';
            setTimeout(() => {
                // Alternar el ícono de ojo abierto/cerrado (usando SVGs inline)
                eyeIcon.innerHTML = type === 'text' ?
                    `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"></path>` :
                    `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>`;
                eyeIcon.style.transform = 'scale(1)';
            }, 150);
        });
    }

    // ----------------------------------------------------
    // 2. Manejador para alternar el modo (Login/Registro)
    // ----------------------------------------------------
    if (toggleModeBtn && form) {
        toggleModeBtn.addEventListener('click', () => {
            isLoginMode = !isLoginMode;
            hideErrorMessage(); // Ocultar errores al cambiar
            
            // Revertir estado del botón
            actionText.textContent = isLoginMode ? 'Iniciar Sesión' : 'Registrarse';
            loadingIcon.classList.add('hidden');
            submitBtn.disabled = false;


            if (isLoginMode) {
                // Modo Iniciar Sesión
                formTitle.textContent = 'Iniciar Sesión';
                formSubtitle.textContent = 'Ingresa tu usuario y contraseña.';
                actionText.textContent = 'Iniciar Sesión';
                toggleModeBtn.innerHTML = '¿No tienes cuenta? <span class="font-bold underline">Regístrate</span>';
                // El formulario apunta a la URL de login de Django
                form.action = "{% url 'usuarios:login' %}"; 
            } else {
                // Modo Registrarse
                formTitle.textContent = 'Crear Cuenta';
                formSubtitle.textContent = 'Ingresa un usuario y una contraseña segura.';
                actionText.textContent = 'Registrarse';
                toggleModeBtn.innerHTML = '¿Ya tienes cuenta? <span class="font-bold underline">Iniciar Sesión</span>';
                // El formulario apunta a la URL de registro de Django
                form.action = "{% url 'usuarios:registro' %}"; 
            }
            // Limpiamos los campos
            form.reset();
        });
    }

    // ----------------------------------------------------
    // 3. Manejador del Formulario (Solo usa Django)
    // ----------------------------------------------------
    if (form) {
        form.addEventListener('submit', async function (e) {
            // No prevenimos el default (e.preventDefault()) para que Django maneje el envío.
            
            hideErrorMessage(); 

            // Mostrar estado de carga
            actionText.textContent = isLoginMode ? 'Iniciando...' : 'Registrando...';
            loadingIcon.classList.remove('hidden');
            submitBtn.disabled = true;

            // El formulario se envía a la URL definida en form.action (Django)
            this.submit(); 
        });
    }

    // ----------------------------------------------------
    // 4. Lógica de Modal y Efectos Visuales
    // ----------------------------------------------------

    // Cerrar modal
    if (closeModal) closeModal.addEventListener('click', () => successModal.classList.add('hidden'));
    if (successModal) successModal.addEventListener('click', (e) => {
        if (e.target === successModal) successModal.classList.add('hidden');
    });

    // Agregar efectos de clic a todos los botones
    document.querySelectorAll('button').forEach(button => {
        button.addEventListener('click', createRipple);
    });
    
    // Efectos de movimiento de ratón (Parallax sutil)
    const mainContainer = document.getElementById('mainContainer');
    document.addEventListener('mousemove', (e) => {
        const mouseX = e.clientX / window.innerWidth;
        const mouseY = e.clientY / window.innerHeight;

        const translateX = (mouseX - 0.5) * 20;
        const translateY = (mouseY - 0.5) * 20;

        if (mainContainer) mainContainer.style.transform = `translate(${translateX}px, ${translateY}px)`;

        const floatingElements = document.querySelectorAll('.floating');
        floatingElements.forEach((element, index) => {
            const speed = (index + 1) * 0.5;
            const x = (mouseX - 0.5) * speed * 10;
            const y = (mouseY - 0.5) * speed * 10;
            element.style.transform += ` translate(${x}px, ${y}px)`;
        });
    });

    // Inicializar efectos de fondo
    createStars();
    setInterval(createParticle, 800);
}

// ----------------------------------------------------
// Funciones de efectos visuales (Independientes)
// ----------------------------------------------------

function createStars() {
    const parallaxBg = document.getElementById('parallaxBg');
    if (!parallaxBg) return;
    for (let i = 0; i < 50; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.width = Math.random() * 3 + 1 + 'px';
        star.style.height = star.style.width;
        star.style.animationDelay = Math.random() * 2 + 's';
        parallaxBg.appendChild(star);
    }
}

function createParticle() {
    const particleContainer = document.getElementById('particleContainer');
    if (!particleContainer) return;

    const particle = document.createElement('div');
    particle.className = 'particle';
    particle.style.left = Math.random() * 100 + '%';
    particle.style.width = Math.random() * 8 + 4 + 'px';
    particle.style.height = particle.style.width;
    particle.style.animationDuration = (Math.random() * 3 + 4) + 's';
    particle.style.animationDelay = Math.random() * 2 + 's';

    particleContainer.appendChild(particle);

    setTimeout(() => { particle.remove(); }, 8000);
}

function createRipple(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return; // Evitar ripples en elementos ocultos

    const ripple = document.createElement('span');
    const size = Math.max(rect.width, rect.height);
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;

    ripple.className = 'ripple';
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';

    e.currentTarget.appendChild(ripple);
    setTimeout(() => { ripple.remove(); }, 600);
}


// Iniciar el DOM y la lógica de la aplicación (SIN Firebase)
window.onload = () => {
    setupApp();
};