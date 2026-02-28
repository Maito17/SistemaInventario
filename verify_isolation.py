import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "possitema.settings")
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from inventario.models import Producto, Categoria

def verify():
    # Clean up
    User.objects.filter(username__in=['usera', 'userb']).delete()
    
    # Create Users
    user_a = User.objects.create_user(username='usera', password='password123')
    user_b = User.objects.create_user(username='userb', password='password123')
    
    print("Users created.")
    
    # Create Product for User A directly (simulating view logic)
    cat_a = Categoria.objects.create(nombre="Cat A", user=user_a)
    prod_a = Producto.objects.create(
        id_producto="PROD-A", 
        nombre="Product A", 
        precio_costo=10, 
        precio_venta=20, 
        cantidad=100, 
        categoria=cat_a,
        user=user_a
    )
    
    print(f"Product {prod_a.nombre} created for {user_a.username}.")
    
    # Verify User B cannot see it via query
    prods_b_query = Producto.objects.filter(user=user_b)
    if prods_b_query.exists():
        print("FAIL: User B can see products via direct query!")
    else:
        print("PASS: User B cannot see products via direct query.")
        
    # Verify User A can see it
    prods_a_query = Producto.objects.filter(user=user_a)
    if prods_a_query.count() == 1:
        print("PASS: User A sees their product.")
    else:
        print(f"FAIL: User A sees {prods_a_query.count()} products, expected 1.")

    # Test View Isolation
    client_a = Client()
    client_a.login(username='usera', password='password123')
    
    client_b = Client()
    client_b.login(username='userb', password='password123')
    
    # Check List View User A
    print("Checking List View for User A...")
    response_a = client_a.get('/inventario/productos/')
    if response_a.status_code == 200:
        if b"Product A" in response_a.content:
             print("PASS: User A sees Product A in list.")
        else:
             print("FAIL: User A does NOT see Product A in list.")
    else:
        print(f"FAIL: Status code {response_a.status_code}")

    # Check List View User B
    print("Checking List View for User B...")
    response_b = client_b.get('/inventario/productos/')
    if response_b.status_code == 200:
        if b"Product A" in response_b.content:
             print("FAIL: User B sees Product A in list!")
        else:
             print("PASS: User B does NOT see Product A in list.")
    else:
        print(f"FAIL: Status code {response_b.status_code}")
        
    # Verify User B causing side effects
    print("User B creating product...")
    cat_b = Categoria.objects.create(nombre="Cat B", user=user_b)
    prod_b = Producto.objects.create(
        id_producto="PROD-B", 
        nombre="Product B", 
        precio_costo=10, 
        precio_venta=20, 
        cantidad=100, 
        categoria=cat_b,
        user=user_b
    )
    
    # Check List View User A again
    response_a_2 = client_a.get('/inventario/productos/')
    if b"Product B" in response_a_2.content:
        print("FAIL: User A sees Product B!")
    else:
        print("PASS: User A does NOT see Product B.")

if __name__ == "__main__":
    verify()
