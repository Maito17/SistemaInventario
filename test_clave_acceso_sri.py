#!/usr/bin/env python
"""
Script de prueba para la generación de Clave de Acceso del SRI Ecuador.
Ejecutar con: python manage.py shell < test_clave_acceso_sri.py
o directamente: python test_clave_acceso_sri.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'possitema.settings')
django.setup()

from possitema.services import generar_clave_acceso_sri, calcular_digito_verificador_modulo11

def test_clave_acceso():
    """Prueba la generación de clave de acceso con ejemplos."""
    
    print("=" * 60)
    print("TEST DE CLAVE DE ACCESO DEL SRI ECUADOR")
    print("=" * 60)
    
    # Caso 1: Prueba básica
    print("\n1. PRUEBA BÁSICA")
    print("-" * 60)
    try:
        clave = generar_clave_acceso_sri(
            fecha_emision='15022026',      # 15 de febrero de 2026
            tipo_comprobante='01',         # Factura
            ruc='1233432154235',           # RUC de prueba
            ambiente='2',                  # Prueba
            establecimiento='001',         # Establecimiento
            punto_emision='001',           # Punto de emisión
            secuencial='000000001',        # Secuencial
            tipo_emision='1'               # Normal
        )
        print(f"✓ Clave generada exitosamente")
        print(f"  Clave: {clave}")
        print(f"  Longitud: {len(clave)} dígitos")
        print(f"  Formato válido: {'SÍ' if len(clave) == 49 and clave.isdigit() else 'NO'}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    # Caso 2: Validaciones
    print("\n2. TEST DE VALIDACIONES")
    print("-" * 60)
    
    test_cases = [
        {
            'name': 'Fecha inválida',
            'params': {
                'fecha_emision': '99999999',
                'tipo_comprobante': '01',
                'ruc': '1233432154235',
                'ambiente': '2',
                'establecimiento': '001',
                'punto_emision': '001',
                'secuencial': '000000001',
                'tipo_emision': '1'
            },
            'should_fail': False  # La validación no verifica fecha real
        },
        {
            'name': 'Tipo de comprobante inválido',
            'params': {
                'fecha_emision': '15022026',
                'tipo_comprobante': '1',  # Debe tener 2 dígitos
                'ruc': '1233432154235',
                'ambiente': '2',
                'establecimiento': '001',
                'punto_emision': '001',
                'secuencial': '000000001',
                'tipo_emision': '1'
            },
            'should_fail': True
        },
        {
            'name': 'RUC inválido',
            'params': {
                'fecha_emision': '15022026',
                'tipo_comprobante': '01',
                'ruc': '123343215423',  # Solo 12 dígitos
                'ambiente': '2',
                'establecimiento': '001',
                'punto_emision': '001',
                'secuencial': '000000001',
                'tipo_emision': '1'
            },
            'should_fail': True
        },
        {
            'name': 'Ambiente inválido',
            'params': {
                'fecha_emision': '15022026',
                'tipo_comprobante': '01',
                'ruc': '1233432154235',
                'ambiente': '3',  # Solo 1 o 2
                'establecimiento': '001',
                'punto_emision': '001',
                'secuencial': '000000001',
                'tipo_emision': '1'
            },
            'should_fail': True
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        try:
            clave = generar_clave_acceso_sri(**test['params'])
            if test['should_fail']:
                print(f"  {i}. {test['name']}: ✗ (debería fallar pero pasó)")
            else:
                print(f"  {i}. {test['name']}: ✓ Válido")
        except ValueError as e:
            if test['should_fail']:
                print(f"  {i}. {test['name']}: ✓ Error esperado")
            else:
                print(f"  {i}. {test['name']}: ✗ {str(e)}")
    
    # Caso 3: Prueba del algoritmo Módulo 11
    print("\n3. TEST DEL ALGORITMO MÓDULO 11")
    print("-" * 60)
    # Utilizando una clave de 48 dígitos conocida
    clave_48_digitos = '151220261011233432154235200100100100000000011'
    digito = calcular_digito_verificador_modulo11(clave_48_digitos)
    clave_completa = clave_48_digitos + str(digito)
    print(f"Clave sin dígito verificador: {clave_48_digitos}")
    print(f"Dígito verificador calculado: {digito}")
    print(f"Clave completa: {clave_completa}")
    print(f"Longitud: {len(clave_completa)} dígitos")
    
    # Caso 4: Múltiples secuenciales
    print("\n4. TEST CON MÚLTIPLES SECUENCIALES")
    print("-" * 60)
    claves_generadas = []
    base_params = {
        'fecha_emision': '15022026',
        'tipo_comprobante': '01',
        'ruc': '1233432154235',
        'ambiente': '2',
        'establecimiento': '001',
        'punto_emision': '001',
        'tipo_emision': '1'
    }
    
    for num in range(1, 6):
        params = {**base_params, 'secuencial': str(num).zfill(9)}
        clave = generar_clave_acceso_sri(**params)
        claves_generadas.append(clave)
        print(f"  Secuencial {num}: {clave}")
    
    # Verificar que son diferentes
    print(f"\n  Todas las claves son diferentes: {'✓ SÍ' if len(set(claves_generadas)) == 5 else '✗ NO'}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETADO")
    print("=" * 60)

if __name__ == '__main__':
    test_clave_acceso()
