from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Gasto, TipoGasto, DetalleGastoAdministracion, DetalleGastoVenta


@login_required
def lista_gastos(request):
    """Muestra el listado de todos los gastos."""
    gastos_list = Gasto.objects.filter(owner=request.user).order_by('-fecha_gasto')
    
    # Filtros
    tipo_filtro = request.GET.get('tipo')
    estado_filtro = request.GET.get('estado')
    
    if tipo_filtro:
        gastos_list = gastos_list.filter(tipo_gasto__nombre=tipo_filtro)
    
    if estado_filtro:
        gastos_list = gastos_list.filter(estado=estado_filtro)
    
    # Paginación
    paginator = Paginator(gastos_list, 10)
    page_number = request.GET.get('page')
    gastos = paginator.get_page(page_number)
    
    tipos_gasto = TipoGasto.objects.filter(owner=request.user)
    
    context = {
        'gastos': gastos,
        'tipos_gasto': tipos_gasto,
        'tipo_filtro': tipo_filtro,
        'estado_filtro': estado_filtro,
    }
    return render(request, 'gasto/lista_gastos.html', context)


@login_required
def crear_gasto(request):
    """Crear un nuevo gasto."""
    if request.method == 'POST':
        tipo_gasto_id = request.POST.get('tipo_gasto')
        descripcion = request.POST.get('descripcion')
        monto = request.POST.get('monto')
        fecha_gasto = request.POST.get('fecha_gasto')
        estado = request.POST.get('estado', 'PENDIENTE')
        notas = request.POST.get('notas', '')
        
        try:
            tipo_gasto = TipoGasto.objects.get(id=tipo_gasto_id, owner=request.user)
            gasto = Gasto.objects.create(
                owner=request.user,
                tipo_gasto=tipo_gasto,
                descripcion=descripcion,
                monto=monto,
                fecha_gasto=fecha_gasto,
                estado=estado,
                notas=notas
            )
            
            # Crear detalles según el tipo
            if tipo_gasto.nombre == 'ADMINISTRACION':
                concepto = request.POST.get('concepto_admin', 'OTROS')
                responsable = request.POST.get('responsable', '')
                DetalleGastoAdministracion.objects.create(
                    gasto=gasto,
                    concepto=concepto,
                    responsable=responsable,
                    owner=request.user
                )
            elif tipo_gasto.nombre == 'VENTA':
                concepto = request.POST.get('concepto_venta', 'OTROS')
                beneficiario = request.POST.get('beneficiario', '')
                canal = request.POST.get('canal', '')
                DetalleGastoVenta.objects.create(
                    gasto=gasto,
                    concepto=concepto,
                    beneficiario=beneficiario,
                    canal=canal,
                    owner=request.user
                )
            
            messages.success(request, f'Gasto "{descripcion}" creado exitosamente.')
            return redirect('gasto:lista_gastos')
        except Exception as e:
            messages.error(request, f'Error al crear gasto: {str(e)}')
    
    tipos_gasto = TipoGasto.objects.filter(owner=request.user)
    context = {
        'tipos_gasto': tipos_gasto,
    }
    return render(request, 'gasto/crear_gasto.html', context)


@login_required
def editar_gasto(request, pk):
    """Editar un gasto existente."""
    gasto = get_object_or_404(Gasto, id_gasto=pk, owner=request.user)
    
    if request.method == 'POST':
        gasto.descripcion = request.POST.get('descripcion')
        gasto.monto = request.POST.get('monto')
        gasto.fecha_gasto = request.POST.get('fecha_gasto')
        gasto.fecha_pago = request.POST.get('fecha_pago') or None
        gasto.estado = request.POST.get('estado')
        gasto.notas = request.POST.get('notas', '')
        gasto.save()
        
        # Actualizar detalles
        if gasto.tipo_gasto.nombre == 'ADMINISTRACION' and hasattr(gasto, 'detalle_admin'):
            gasto.detalle_admin.concepto = request.POST.get('concepto_admin', 'OTROS')
            gasto.detalle_admin.responsable = request.POST.get('responsable', '')
            gasto.detalle_admin.save()
        elif gasto.tipo_gasto.nombre == 'VENTA' and hasattr(gasto, 'detalle_venta'):
            gasto.detalle_venta.concepto = request.POST.get('concepto_venta', 'OTROS')
            gasto.detalle_venta.beneficiario = request.POST.get('beneficiario', '')
            gasto.detalle_venta.canal = request.POST.get('canal', '')
            gasto.detalle_venta.save()
        
        messages.success(request, f'Gasto actualizado exitosamente.')
        return redirect('gasto:lista_gastos')
    
    context = {
        'gasto': gasto,
    }
    return render(request, 'gasto/editar_gasto.html', context)


@login_required
def eliminar_gasto(request, pk):
    """Eliminar un gasto."""
    gasto = get_object_or_404(Gasto, id_gasto=pk, owner=request.user)
    
    if request.method == 'POST':
        gasto.delete()
        messages.success(request, 'Gasto eliminado exitosamente.')
        return redirect('gasto:lista_gastos')
    
    context = {
        'gasto': gasto,
    }
    return render(request, 'gasto/confirmar_eliminar.html', context)


@login_required
def detalle_gasto(request, pk):
    """Ver detalles de un gasto."""
    gasto = get_object_or_404(Gasto, id_gasto=pk, owner=request.user)
    context = {
        'gasto': gasto,
    }
    return render(request, 'gasto/detalle_gasto.html', context)


@login_required
def lista_detalles_admin(request):
    """Muestra el listado de detalles de gastos de administración."""
    detalles = DetalleGastoAdministracion.objects.filter(gasto__owner=request.user).select_related('gasto').order_by('-gasto__fecha_gasto')
    
    # Paginación
    paginator = Paginator(detalles, 15)
    page_number = request.GET.get('page')
    detalles_paginated = paginator.get_page(page_number)
    
    context = {
        'detalles': detalles_paginated,
    }
    return render(request, 'gasto/lista_detalles_admin.html', context)


@login_required
def lista_detalles_venta(request):
    """Muestra el listado de detalles de gastos de venta."""
    detalles = DetalleGastoVenta.objects.filter(gasto__owner=request.user).select_related('gasto').order_by('-gasto__fecha_gasto')
    
    # Paginación
    paginator = Paginator(detalles, 15)
    page_number = request.GET.get('page')
    detalles_paginated = paginator.get_page(page_number)
    
    context = {
        'detalles': detalles_paginated,
    }
    return render(request, 'gasto/lista_detalles_venta.html', context)


@login_required
def lista_tipos_gasto(request):
    """Muestra el listado de tipos de gastos."""
    tipos = TipoGasto.objects.filter(owner=request.user).order_by('nombre')
    
    context = {
        'tipos': tipos,
    }
    return render(request, 'gasto/lista_tipos.html', context)
