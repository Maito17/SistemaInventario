# usuarios/views.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group, Permission
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import JsonResponse
from .forms import SignUpForm
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
from datetime import timedelta

# Simulación de almacenamiento de tokens (usar modelo en producción)
password_reset_tokens = {}


def registro_view(request):
    """Vista para el registro de nuevos usuarios"""
    if request.user.is_authenticated:
        return redirect('possitema:dashboard')
        
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Asignar permiso básico de acceso al POS
            try:
                permission = Permission.objects.get(codename='can_access_pos', content_type__app_label='possitema')
                user.user_permissions.add(permission)
            except Permission.DoesNotExist:
                pass
                
            # Lógica de suscripción eliminada

            login(request, user)
            messages.success(request, f'¡Bienvenido {user.get_full_name()}! Tu cuenta ha sido creada.')
            return redirect('possitema:dashboard')
        else:
            messages.error(request, 'Por favor corrige los errores abajo.')
    else:
        form = SignUpForm()
    
    return render(request, 'usuarios/registro.html', {'form': form})

@login_required
def fix_my_permissions(request):
    """Vista de utilidad para arreglar permisos del usuario actual"""
    try:
        # Asegurar que el permiso existe
        from django.contrib.auth.models import Permission, ContentType
        from possitema.models import ControlAcceso
        
        content_type = ContentType.objects.get_for_model(ControlAcceso)
        permission, created = Permission.objects.get_or_create(
            codename='can_access_pos',
            content_type=content_type,
            defaults={'name': 'Puede acceder al punto de venta'}
        )
        
        # Asignar al usuario
        request.user.user_permissions.add(permission)
        
        # También asegurar que existe PerfilUsuario si se necesita
        # (Aunque por ahora solo el permiso es crítico)
        
        messages.success(request, 'Permisos reparados exitosamente. Ahora deberías poder entrar.')
        return redirect('possitema:dashboard')
    except Exception as e:
        messages.error(request, f'Error reparando permisos: {str(e)}')
        return redirect('usuarios:login')

def login_view(request):
    """Vista personalizada para el login"""
    # Si el usuario ya está autenticado, redirigir
    if request.user.is_authenticated:
        # Solo redirigir si NO está en proceso de recuperación de contraseña
        if not request.GET.get('reset'):
            return redirect('possitema:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        # Autenticar usuario
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'✓ Bienvenido {user.get_full_name() or user.username}')
            return redirect('possitema:dashboard')
        else:
            error_message = 'Usuario o contraseña incorrectos. Por favor, intenta de nuevo.'
            return render(request, 'usuarios/login.html', {
                'error_message': error_message
            })
    # GET request - mostrar el formulario
    return render(request, 'usuarios/login.html')


def logout_view(request):
    """Vista personalizada para el logout"""
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('usuarios:login')


# ==================== GESTIÓN DE USUARIOS ====================

@login_required
def lista_usuarios(request):
    """Vista para listar todos los usuarios"""
    query = request.GET.get('q', '')
    
    if request.user.is_superuser:
        # Superusuario ve todos los usuarios normales (no staff, no superuser)
        if query:
            usuarios = User.objects.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            ).filter(is_superuser=False, is_staff=False).order_by('username')
        else:
            usuarios = User.objects.filter(is_superuser=False, is_staff=False).order_by('username')
    else:
        if query:
            usuarios = User.objects.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            ).filter(perfilusuario__owner=request.user).order_by('username')
        else:
            usuarios = User.objects.filter(perfilusuario__owner=request.user).order_by('username')
    
    context = {
        'usuarios': usuarios,
        'query': query,
    }
    return render(request, 'usuarios/lista_usuarios.html', context)




def crear_usuario(request):
    """Vista para crear un nuevo usuario, respetando el límite del plan."""
    if not verificar_limite_usuarios(request.user):
        messages.error(request, "Has alcanzado el límite de usuarios de tu plan. Mejora tu suscripción para agregar más usuarios.")
        return redirect('usuarios:lista_usuarios')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active', 'on') == 'on'
        groups = request.POST.getlist('groups')
        
        # Validaciones
        if not username:
            messages.error(request, 'El nombre de usuario es requerido.')
            return redirect('usuarios:crear_usuario')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe.')
            return redirect('usuarios:crear_usuario')
        
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('usuarios:crear_usuario')
        
        if len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            return redirect('usuarios:crear_usuario')
        
        # Crear usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
            is_active=is_active
        )

        # Asignar dueño (owner) y datos de perfil (rol, teléfono, dirección)
        from .models import PerfilUsuario
        rol_value = request.POST.get('rol', 'Empleado')
        telefono_value = request.POST.get('telefono', '')
        direccion_value = request.POST.get('direccion', '')
        PerfilUsuario.objects.create(
            user=user,
            owner=request.user,
            rol=rol_value,
            telefono=telefono_value,
            direccion=direccion_value
        )
        
        # Asignar permisos básicos (acceso a POS) por defecto
        from django.contrib.auth.models import Permission
        try:
            permission = Permission.objects.get(codename='can_access_pos', content_type__app_label='possitema')
            user.user_permissions.add(permission)
        except Permission.DoesNotExist:
            pass

        # Asignar grupos
        if groups:
            user.groups.set(groups)
        
        messages.success(request, f'Usuario {username} creado exitosamente.')
        return redirect('usuarios:lista_usuarios')
    
    # GET - mostrar formulario
    grupos = Group.objects.all().order_by('name')
    context = {
        'grupos': grupos,
    }
    return render(request, 'usuarios/crear_usuario.html', context)


@login_required
@permission_required('auth.change_user', raise_exception=True)
def editar_usuario(request, user_id):
    """Vista para editar un usuario existente"""
    usuario = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        usuario.username = request.POST.get('username', usuario.username)
        usuario.email = request.POST.get('email', '')
        usuario.first_name = request.POST.get('first_name', '')
        usuario.last_name = request.POST.get('last_name', '')
        usuario.is_staff = request.POST.get('is_staff') == 'on'
        usuario.is_active = request.POST.get('is_active', 'on') == 'on'
        
        # Cambiar contraseña solo si se proporciona
        new_password = request.POST.get('new_password')
        if new_password:
            password_confirm = request.POST.get('password_confirm')
            if new_password == password_confirm:
                usuario.set_password(new_password)
            else:
                messages.error(request, 'Las contraseñas no coinciden.')
                return redirect('usuarios:editar_usuario', user_id=user_id)
        
        usuario.save()

        # Actualizar o crear PerfilUsuario con campos opcionales
        from .models import PerfilUsuario
        rol_value = request.POST.get('rol', None)
        telefono_value = request.POST.get('telefono', None)
        direccion_value = request.POST.get('direccion', None)
        perfil, created = PerfilUsuario.objects.get_or_create(user=usuario, defaults={
            'owner': request.user,
            'rol': rol_value or 'Empleado',
            'telefono': telefono_value or '',
            'direccion': direccion_value or '',
        })
        if not created:
            if rol_value is not None:
                perfil.rol = rol_value
            if telefono_value is not None:
                perfil.telefono = telefono_value
            if direccion_value is not None:
                perfil.direccion = direccion_value
            perfil.save()

        # Actualizar grupos
        groups = request.POST.getlist('groups')
        usuario.groups.set(groups)
        
        messages.success(request, f'Usuario {usuario.username} actualizado exitosamente.')
        return redirect('usuarios:lista_usuarios')
    
    # GET - mostrar formulario
    grupos = Group.objects.all().order_by('name')
    grupos_usuario = usuario.groups.all().values_list('id', flat=True)
    
    context = {
        'usuario': usuario,
        'grupos': grupos,
        'grupos_usuario': list(grupos_usuario),
    }
    return render(request, 'usuarios/editar_usuario.html', context)


@login_required
@permission_required('auth.delete_user', raise_exception=True)
def eliminar_usuario(request, user_id):
    """Vista para eliminar un usuario"""
    usuario = get_object_or_404(User, pk=user_id)
    
    # Prevenir que el usuario se elimine a sí mismo
    if usuario == request.user:
        messages.error(request, 'No puedes eliminar tu propio usuario.')
        return redirect('usuarios:lista_usuarios')
    
    if request.method == 'POST':
        username = usuario.username
        usuario.delete()
        messages.success(request, f'Usuario {username} eliminado exitosamente.')
        return redirect('usuarios:lista_usuarios')
    
    context = {
        'usuario': usuario,
    }
    return render(request, 'usuarios/eliminar_usuario.html', context)


# ==================== GESTIÓN DE ROLES/GRUPOS ====================

@login_required
def lista_roles(request):
    """Vista para listar todos los roles (grupos)"""
    query = request.GET.get('q', '')
    
    if query:
        roles = Group.objects.filter(name__icontains=query, perfil__owner=request.user).order_by('name')
    else:
        roles = Group.objects.filter(perfil__owner=request.user).order_by('name')
    
    context = {
        'roles': roles,
        'query': query,
    }
    return render(request, 'usuarios/lista_roles.html', context)


@login_required
def crear_rol(request):
    """Vista para crear un nuevo rol (grupo)"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        permisos = request.POST.getlist('permisos')
        
        if not nombre:
            messages.error(request, 'El nombre del rol es requerido.')
            return redirect('usuarios:crear_rol')
        
        if Group.objects.filter(name=nombre).exists():
            messages.error(request, 'Ya existe un rol con ese nombre.')
            return redirect('usuarios:crear_rol')
        
        # Crear grupo
        grupo = Group.objects.create(name=nombre)
        
        # Asignar permisos
        if permisos:
            grupo.permissions.set(permisos)

        # Crear perfil del grupo con owner para mantener independencia
        from .models import PerfilGrupo
        try:
            PerfilGrupo.objects.create(group=grupo, owner=request.user)
        except Exception:
            # No bloquear la creación si no se puede crear el perfil
            pass

        messages.success(request, f'Rol {nombre} creado exitosamente.')
        return redirect('usuarios:lista_roles')
    
    # GET - mostrar formulario
    permisos = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename')
    
    context = {
        'permisos': permisos,
    }
    return render(request, 'usuarios/crear_rol.html', context)


@login_required
@permission_required('auth.change_group', raise_exception=True)
def editar_rol(request, group_id):
    """Vista para editar un rol (grupo) existente"""
    rol = get_object_or_404(Group, pk=group_id)
    # Verificar que el rol pertenezca al owner actual
    try:
        if rol.perfil.owner_id != request.user.id:
            messages.error(request, 'No tienes permiso para editar este rol.')
            return redirect('usuarios:lista_roles')
    except Exception:
        messages.error(request, 'No tienes permiso para editar este rol.')
        return redirect('usuarios:lista_roles')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        permisos = request.POST.getlist('permisos')
        
        if not nombre:
            messages.error(request, 'El nombre del rol es requerido.')
            return redirect('usuarios:editar_rol', group_id=group_id)
        
        rol.name = nombre
        rol.save()
        
        # Actualizar permisos
        rol.permissions.set(permisos)
        
        messages.success(request, f'Rol {nombre} actualizado exitosamente.')
        return redirect('usuarios:lista_roles')
    
    # GET - mostrar formulario
    permisos = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename')
    permisos_rol = rol.permissions.all().values_list('id', flat=True)
    
    context = {
        'rol': rol,
        'permisos': permisos,
        'permisos_rol': list(permisos_rol),
    }
    return render(request, 'usuarios/editar_rol.html', context)


@login_required
@permission_required('auth.delete_group', raise_exception=True)
def eliminar_rol(request, group_id):
    """Vista para eliminar un rol (grupo)"""
    rol = get_object_or_404(Group, pk=group_id)
    # Verificar que el rol pertenezca al owner actual
    try:
        if rol.perfil.owner_id != request.user.id:
            messages.error(request, 'No tienes permiso para eliminar este rol.')
            return redirect('usuarios:lista_roles')
    except Exception:
        messages.error(request, 'No tienes permiso para eliminar este rol.')
        return redirect('usuarios:lista_roles')
    
    if request.method == 'POST':
        nombre = rol.name
        rol.delete()
        messages.success(request, f'Rol {nombre} eliminado exitosamente.')
        return redirect('usuarios:lista_roles')
    
    # Contar usuarios con este rol
    usuarios_count = rol.user_set.count()
    
    context = {
        'rol': rol,
        'usuarios_count': usuarios_count,
    }
    return render(request, 'usuarios/eliminar_rol.html', context)


# ==================== GESTIÓN DE PERSONAL ====================

@login_required
@login_required
@login_required
def dashboard_personal(request):
    """Panel de control del personal con estado de entrada/salida y caja"""
    from control.models import RegistroAsistencia
    from .models import EstadoCaja
    from django.utils import timezone
    from datetime import date
    
    # Obtener el usuario actual
    usuario = request.user
    
    # Obtener el registro de hoy desde control.RegistroAsistencia
    hoy = date.today()
    registro_hoy = RegistroAsistencia.objects.filter(
        usuario=usuario,
        fecha=hoy
    ).first()
    
    # Si existe, refrescar desde BD
    if registro_hoy:
        registro_hoy.refresh_from_db()
    
    # Obtener estado de caja de hoy (la última caja de hoy, puede estar abierta o cerrada)
    estado_caja_hoy = EstadoCaja.objects.filter(
        user=usuario,
        fecha=hoy
    ).order_by('-timestamp_apertura').first()
    
    # Si existe, refrescar desde BD
    if estado_caja_hoy:
        estado_caja_hoy.refresh_from_db()
    
    context = {
        'registro_hoy': registro_hoy,
        'estado_caja_hoy': estado_caja_hoy,
        'usuario_nombre': usuario.get_full_name() or usuario.username,
    }
    return render(request, 'usuarios/dashboard_personal.html', context)


@login_required
def lista_personal(request):
    """Lista de todos los trabajadores con su estatus - Solo para admins"""
    from .models import EstadoCaja, RegistroAcceso
    from datetime import timedelta
    from django.utils import timezone
    
    # Todos los usuarios autenticados pueden ver la tabla de personal
    
    from django.db.models import Q
    if request.user.is_superuser:
        # Superusuario ve todos los usuarios normales (no staff, no superuser)
        usuarios = User.objects.filter(is_superuser=False, is_staff=False).exclude(username='admin').order_by('first_name')
    else:
        # Usuario normal ve solo los que le corresponden
        usuarios = User.objects.filter(
            Q(perfilusuario__owner=request.user) | Q(pk=request.user.pk)
        ).exclude(username='admin').order_by('first_name')
    
    # Obtener la fecha de hoy en la zona horaria local
    ahora = timezone.now()
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_dia = inicio_dia + timedelta(days=1)
    
    # Crear lista con información de cada usuario
    personal_info = []
    for user in usuarios:
        # Obtener el último LOGIN de hoy
        ultimo_login = RegistroAcceso.objects.filter(
            user=user,
            tipo_evento='LOGIN',
            fecha_hora__gte=inicio_dia,
            fecha_hora__lt=fin_dia
        ).order_by('-fecha_hora').first()
        
        # Obtener el último LOGOUT de hoy
        ultimo_logout = RegistroAcceso.objects.filter(
            user=user,
            tipo_evento='LOGOUT',
            fecha_hora__gte=inicio_dia,
            fecha_hora__lt=fin_dia
        ).order_by('-fecha_hora').first()
        
        # Verificar si hay una sesión activa (login sin logout después)
        sesion_activa = False
        if ultimo_login and not ultimo_logout:
            sesion_activa = True
        elif ultimo_login and ultimo_logout:
            sesion_activa = ultimo_login.fecha_hora > ultimo_logout.fecha_hora
        
        # Buscar el estado de caja de hoy (usando la misma lógica de fecha)
        estado_caja = EstadoCaja.objects.filter(
            user=user,
            fecha__gte=inicio_dia.date(),
            fecha__lt=fin_dia.date()
        ).order_by('-timestamp_apertura').first()
        
        personal_info.append({
            'usuario': user,
            'ultimo_login': ultimo_login,
            'ultimo_logout': ultimo_logout,
            'sesion_activa': sesion_activa,
            'estado_caja': estado_caja,
        })
    
    context = {
        'personal': personal_info,
    }
    return render(request, 'usuarios/lista_personal.html', context)


@login_required
@login_required
def registrar_entrada(request):
    """
    DEPRECATED: La entrada se registra automáticamente al hacer login.
    Esta vista se mantiene por compatibilidad pero solo redirige.
    """
    messages.info(request, 'ℹ️ La entrada se registra automáticamente al iniciar sesión.')
    return redirect('usuarios:dashboard_personal')


@login_required
def registrar_salida(request):
    """
    DEPRECATED: La salida se registra automáticamente al hacer logout.
    Esta vista se mantiene por compatibilidad pero solo redirige.
    """
    messages.info(request, 'ℹ️ La salida se registra automáticamente al cerrar sesión.')
    return redirect('usuarios:dashboard_personal')


@login_required
def abrir_caja(request):
    """Abrir la caja del usuario"""
    from .models import EstadoCaja
    from django.utils import timezone
    from datetime import date
    
    if request.method != 'POST':
        return redirect('usuarios:dashboard_personal')
    
    usuario = request.user
    hoy = date.today()
    
    # Verificar si ya hay una caja abierta hoy
    caja_abierta = EstadoCaja.objects.filter(
        user=usuario,
        fecha=hoy,
        estado='ABIERTA'
    ).exists()
    
    if caja_abierta:
        messages.warning(request, '✓ Ya tienes una caja abierta hoy.')
    else:
        try:
            monto_inicial_str = request.POST.get('monto_inicial', '0')
            try:
                monto_inicial = float(monto_inicial_str)
            except ValueError:
                monto_inicial = 0.0
            
            caja = EstadoCaja.objects.create(
                user=usuario,
                fecha=hoy,
                estado='ABIERTA',
                monto_inicial=monto_inicial,
                timestamp_apertura=timezone.now()
            )
            
            messages.success(request, f'✓ Caja abierta correctamente con monto inicial: ${monto_inicial:.2f}')
        except Exception as e:
            messages.error(request, f'Error al abrir caja: {str(e)}')
    
    return redirect('usuarios:dashboard_personal')


@login_required
def cerrar_caja(request):
    """Cerrar la caja del usuario"""
    from .models import EstadoCaja
    from django.utils import timezone
    from datetime import date
    
    usuario = request.user
    hoy = date.today()
    
    if request.method != 'POST':
        # GET - mostrar formulario
        estado_caja = EstadoCaja.objects.filter(
            user=usuario,
            fecha=hoy,
            estado='ABIERTA'
        ).first()
        
        if not estado_caja:
            messages.error(request, '❌ No tienes una caja abierta.')
            return redirect('usuarios:dashboard_personal')
        
        context = {
            'estado_caja': estado_caja,
        }
        return render(request, 'usuarios/cerrar_caja.html', context)
    
    # POST - procesar cierre
    estado_caja = EstadoCaja.objects.filter(
        user=usuario,
        fecha=hoy,
        estado='ABIERTA'
    ).first()
    
    if not estado_caja:
        messages.error(request, '❌ No tienes una caja abierta.')
        return redirect('usuarios:dashboard_personal')
    
    try:
        monto_cierre_str = request.POST.get('monto_cierre', '0')
        try:
            monto_cierre = float(monto_cierre_str)
        except ValueError:
            monto_cierre = 0.0
        
        observaciones = request.POST.get('observaciones', '')
        
        estado_caja.estado = 'CERRADA'
        estado_caja.monto_cierre = monto_cierre
        estado_caja.timestamp_cierre = timezone.now()
        estado_caja.observaciones = observaciones
        estado_caja.save()
        
        messages.success(request, f'✓ Caja cerrada correctamente. Monto de cierre: ${monto_cierre:.2f}')
    except Exception as e:
        messages.error(request, f'Error al cerrar caja: {str(e)}')
    
    return redirect('usuarios:dashboard_personal')


# ==================== REGISTRO DE ACCESO (ENTRADA/SALIDA) ====================

@login_required
@permission_required('auth.view_user', raise_exception=True)
def registro_acceso(request):
    """
    Vista para que el administrador vea los registros de entrada/salida de usuarios.
    Muestra un historial de accesos con filtros por usuario y rango de fechas.
    """
    from .models import RegistroAcceso
    from django.utils import timezone
    from datetime import timedelta, date
    
    # Obtener parámetros de filtro
    usuario_id = request.GET.get('usuario_id')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    tipo_evento = request.GET.get('tipo_evento')
    
    # Inicializar queryset
    registros = RegistroAcceso.objects.select_related('user').order_by('-fecha_hora')
    
    # Filtrar por usuario
    if usuario_id:
        registros = registros.filter(user_id=usuario_id)
    
    # Filtrar por tipo de evento (LOGIN/LOGOUT)
    if tipo_evento:
        registros = registros.filter(tipo_evento=tipo_evento)
    
    # Filtrar por rango de fechas
    if fecha_inicio:
        try:
            fecha_inicio_dt = timezone.datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            registros = registros.filter(fecha_hora__date__gte=fecha_inicio_dt)
        except:
            pass
    
    if fecha_fin:
        try:
            fecha_fin_dt = timezone.datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            # Agregar un día para incluir todo el día fin
            fecha_fin_dt = fecha_fin_dt + timedelta(days=1)
            registros = registros.filter(fecha_hora__date__lt=fecha_fin_dt)
        except:
            pass
    
    # Obtener todos los usuarios para el dropdown — solo mis usuarios y yo
    from django.db.models import Q
    usuarios = User.objects.filter(
        Q(perfilusuario__owner=request.user) | Q(pk=request.user.pk)
    ).order_by('first_name', 'last_name')
    
    # Paginar resultados (50 por página)
    from django.core.paginator import Paginator
    paginator = Paginator(registros, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'registros': page_obj.object_list,
        'usuarios': usuarios,
        'usuario_id_seleccionado': int(usuario_id) if usuario_id else None,
        'fecha_inicio': fecha_inicio or '',
        'fecha_fin': fecha_fin or '',
        'tipo_evento_seleccionado': tipo_evento or '',
        'total_registros': registros.count(),
    }
    
    return render(request, 'usuarios/registro_acceso.html', context)


@login_required
@permission_required('auth.view_user', raise_exception=True)
def registro_acceso_usuario(request, user_id):
    """
    Vista para ver el historial de acceso de un usuario específico.
    Útil para reportes personalizados.
    """
    from .models import RegistroAcceso
    from django.utils import timezone
    from datetime import timedelta
    
    usuario = get_object_or_404(User, pk=user_id)

    # Verificar que el usuario objetivo sea propietario del usuario actual (owner) o sea el mismo
    from .models import PerfilUsuario
    propietario_id = None
    try:
        propietario_id = usuario.perfilusuario.owner_id
    except PerfilUsuario.DoesNotExist:
        propietario_id = None

    if usuario != request.user and propietario_id != request.user.id:
        messages.error(request, 'No tienes permiso para ver el historial de ese usuario.')
        return redirect('usuarios:lista_personal')
    
    # Obtener parámetros de filtro
    dias = request.GET.get('dias', '30')  # Últimos 30 días por defecto
    
    try:
        dias = int(dias)
    except:
        dias = 30
    
    # Calcular fecha inicial
    fecha_inicio = timezone.now() - timedelta(days=dias)
    
    # Obtener registros
    registros = RegistroAcceso.objects.filter(
        user=usuario,
        fecha_hora__gte=fecha_inicio
    ).order_by('-fecha_hora')
    
    # Estadísticas
    total_logins = registros.filter(tipo_evento='LOGIN').count()
    total_logouts = registros.filter(tipo_evento='LOGOUT').count()
    
    # Calcular tiempo promedio de sesión
    logins = registros.filter(tipo_evento='LOGIN')
    logouts = registros.filter(tipo_evento='LOGOUT')
    
    tiempo_promedio = None
    if logouts:
        total_duracion = sum([
            r.duracion_sesion.total_seconds() 
            for r in logouts 
            if r.duracion_sesion
        ]) or 0
        tiempo_promedio = total_duracion / logouts.count() if logouts.count() > 0 else None
    
    context = {
        'usuario': usuario,
        'registros': registros,
        'dias': dias,
        'total_logins': total_logins,
        'total_logouts': total_logouts,
        'tiempo_promedio_segundos': int(tiempo_promedio) if tiempo_promedio else None,
    }
    
    return render(request, 'usuarios/registro_acceso_usuario.html', context)


@login_required
@permission_required('auth.view_user', raise_exception=True)
def estadisticas_acceso(request):
    """
    Vista de estadísticas generales de acceso.
    Muestra información agregada de logins, usuarios activos, etc.
    """
    from .models import RegistroAcceso
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Q
    
    # Parámetros
    dias = request.GET.get('dias', '30')
    
    try:
        dias = int(dias)
    except:
        dias = 30
    
    fecha_inicio = timezone.now() - timedelta(days=dias)
    
    # Registros del período — solo para usuarios que yo creé
    from django.db.models import Q
    registros = RegistroAcceso.objects.filter(fecha_hora__gte=fecha_inicio, user__perfilusuario__owner=request.user)
    
    # Estadísticas generales
    total_logins = registros.filter(tipo_evento='LOGIN').count()
    total_logouts = registros.filter(tipo_evento='LOGOUT').count()
    usuarios_activos = registros.filter(tipo_evento='LOGIN').values_list('user', flat=True).distinct().count()
    
    # Top 10 usuarios más activos
    usuarios_mas_activos = registros.filter(
        tipo_evento='LOGIN'
    ).values('user__first_name', 'user__last_name', 'user__username').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Último acceso de cada usuario
    ultimo_acceso_usuarios = []
    usuarios = User.objects.filter(
        Q(perfilusuario__owner=request.user) | Q(pk=request.user.pk)
    ).exclude(username='admin')
    for user in usuarios:
        ultimo_login = RegistroAcceso.objects.filter(
            user=user,
            tipo_evento='LOGIN'
        ).order_by('-fecha_hora').first()
        
        if ultimo_login:
            ultimo_acceso_usuarios.append({
                'usuario': user,
                'ultimo_acceso': ultimo_login.fecha_hora,
                'dias_sin_acceso': (timezone.now() - ultimo_login.fecha_hora).days,
            })
    
    # Ordenar por último acceso
    ultimo_acceso_usuarios.sort(key=lambda x: x['ultimo_acceso'], reverse=True)
    
    context = {
        'dias': dias,
        'total_logins': total_logins,
        'total_logouts': total_logouts,
        'usuarios_activos': usuarios_activos,
        'usuarios_mas_activos': usuarios_mas_activos,
        'ultimo_acceso_usuarios': ultimo_acceso_usuarios,
        'fecha_inicio': fecha_inicio,
    }
    
    return render(request, 'usuarios/estadisticas_acceso.html', context)


def password_reset_request(request):
    error = success = None
    show_password_reset = True
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            token = get_random_string(32)
            password_reset_tokens[token] = {
                'user_id': user.id,
                'expires': timezone.now() + timedelta(hours=1)
            }
            reset_url = request.build_absolute_uri(f'/usuarios/password_reset_confirm/?token={token}')
            send_mail(
                'Recuperación de contraseña',
                f'Para restablecer tu contraseña haz clic aquí: {reset_url}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            success = 'Te hemos enviado un correo con el enlace para restablecer tu contraseña.'
        except User.DoesNotExist:
            error = 'No existe una cuenta con ese correo.'
        except Exception as e:
            import traceback
            error = f'Error inesperado: {str(e)}'
            print('Error en password_reset_request:', traceback.format_exc())
    return render(request, 'usuarios/login.html', {'error': error, 'success': success, 'show_password_reset': show_password_reset})

def password_reset_confirm(request):
    from django.contrib.auth import logout
    logout(request)
    error = success = None
    token = request.GET.get('token')
    data = password_reset_tokens.get(token)
    if not data or data['expires'] < timezone.now():
        error = 'El enlace es inválido o ha expirado.'
    elif request.method == 'POST':
        new_password = request.POST.get('new_password')
        user = User.objects.get(id=data['user_id'])
        user.password = make_password(new_password)
        user.save()
        success = 'Tu contraseña ha sido cambiada exitosamente.'
        del password_reset_tokens[token]
    return render(request, 'usuarios/password_reset_confirm.html', {'error': error, 'success': success})

