//static/dist/js/base.js
$(document).ready(function() {
    // Obtiene la URL actual de la ventana.
    var url = window.location.href;
    
    // Itera sobre todos los enlaces del menú lateral (sidebar)
    $('.nav-sidebar a').each(function() {
        // Si el href del enlace coincide con la URL actual...
        if (this.href === url) {
            // Resalta el enlace como activo
            $(this).addClass('active');
            
            // Si el enlace activo pertenece a un submenú (.nav-treeview)...
            if ($(this).parents('.nav-treeview').length) {
                // 1. Abre el elemento padre del submenú
                $(this).closest('.nav-item').addClass('menu-open');
                // 2. Resalta también el enlace padre
                $(this).closest('.nav-item').children('a').addClass('active');
            }
        }
    });
});
